"""
Integracao com PagSeguro/PagBank para pagamento de presentes.
Suporta PIX, cartao de credito e debito.
"""

import json
import logging
import os
import time

import psycopg2
import requests
from dotenv import load_dotenv
from flask import Blueprint, jsonify, render_template, request
from psycopg2.extras import RealDictCursor

from db import get_connection

load_dotenv()

logger = logging.getLogger(__name__)

PAGBANK_API_URL = os.getenv("PAGBANK_API_URL", "https://api.pagseguro.com").rstrip("/")
PAGBANK_ENV = os.getenv("PAGBANK_ENV", "production").strip().lower()
PAGBANK_SELLER_EMAIL = os.getenv("PAGBANK_SELLER_EMAIL", "").strip().lower()

pagamentos_bp = Blueprint("pagamentos", __name__)


def get_pagbank_token():
    """Le o token atual do ambiente sem usar credenciais hardcoded."""
    return os.getenv("PAGBANK_TOKEN", "").strip()


def log_pagbank_token_status(contexto):
    token = get_pagbank_token()
    logger.info("PagBank token status (%s): configurado=%s", contexto, "sim" if token else "nao")
    return token


def get_pagbank_headers(contexto):
    token = log_pagbank_token_status(contexto)
    if not token:
        raise RuntimeError("PAGBANK_TOKEN nao configurado no ambiente do backend.")

    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


log_pagbank_token_status("import")


def get_pagamentos_table_config(cur):
    """Detecta a tabela de pagamentos disponivel no banco."""
    cur.execute(
        """
        SELECT table_name, column_name
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name IN ('pagamentos_presentes', 'pagamentos_mercado_pago')
        """
    )

    rows = cur.fetchall()
    tables = {}
    for table_name, column_name in rows:
        tables.setdefault(table_name, set()).add(column_name)

    if "pagamentos_presentes" in tables:
        return {"table": "pagamentos_presentes"}

    if "pagamentos_mercado_pago" in tables:
        return {"table": "pagamentos_mercado_pago"}

    raise Exception(
        "Tabela de pagamentos nao encontrada. Esperado: pagamentos_presentes ou pagamentos_mercado_pago"
    )


def gerar_pagamento_id_temporario():
    """Gera um ID temporario unico antes do webhook devolver o ID real."""
    return -int(time.time_ns())


def valor_em_centavos(valor):
    return int(round(float(valor) * 100))


def normalizar_telefone(telefone):
    return "".join(ch for ch in (telefone or "") if ch.isdigit())


def montar_reference_id(presente_id, email_pagador):
    referencia = f"presente_{presente_id}_{time.time_ns()}"
    return referencia[:64]


def extrair_checkout_url_pagbank(checkout):
    for link in checkout.get("links", []):
        if link.get("rel") == "PAY" and link.get("href"):
            return link["href"]

    return None


def get_public_base_url():
    base_url = os.getenv("BASE_URL", "").strip().rstrip("/")
    if base_url:
        return base_url

    return request.host_url.rstrip("/")


def get_presente_by_id(presente_id):
    """Busca um presente no banco de dados pelo ID."""
    conn = None
    cur = None

    try:
        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(
            """
            SELECT *
            FROM presentes
            WHERE id = %s
            """,
            (presente_id,),
        )

        presente = cur.fetchone()
        logger.info("Resultado da busca do presente %s: %s", presente_id, presente)

        if not presente:
            return None

        presente = dict(presente)
        presente["titulo"] = presente.get("titulo") or presente.get("nome") or "Presente"
        presente["descricao"] = presente.get("descricao") or presente.get("nome") or ""
        presente["valor_sugerido"] = presente.get("valor_sugerido")
        if presente["valor_sugerido"] is None:
            presente["valor_sugerido"] = presente.get("valor")
        presente["status"] = presente.get("status") or "disponivel"
        return presente

    except psycopg2.Error as e:
        logger.error("Erro ao buscar presente %s: %s", presente_id, e)
        return None
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


def salvar_pagamento_no_banco(
    presente_id,
    nome_pagador,
    email_pagador,
    telefone_pagador,
    mensagem_pagador,
    valor,
    preferencia_id,
    init_point,
):
    """Salva o pagamento na tabela de pagamentos disponivel."""
    conn = None
    cur = None

    try:
        conn = get_connection()
        cur = conn.cursor()
        table_config = get_pagamentos_table_config(cur)

        if table_config["table"] == "pagamentos_presentes":
            cur.execute(
                """
                INSERT INTO pagamentos_presentes
                (presente_id, nome_pagador, email_pagador, telefone_pagador,
                 mensagem_pagador, valor, status_pagamento)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    presente_id,
                    nome_pagador,
                    email_pagador,
                    telefone_pagador,
                    mensagem_pagador,
                    valor,
                    "pendente",
                ),
            )
        else:
            cur.execute(
                """
                INSERT INTO pagamentos_mercado_pago
                (presente_id, mercado_pago_id, status, valor, nome_pagador,
                 email_pagador, telefone_pagador, mensagem_pagador, preferencia_id, init_point)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    presente_id,
                    gerar_pagamento_id_temporario(),
                    "pending",
                    valor,
                    nome_pagador,
                    email_pagador,
                    telefone_pagador,
                    mensagem_pagador,
                    preferencia_id,
                    init_point,
                ),
            )

        pagamento_id = cur.fetchone()[0]
        conn.commit()
        return pagamento_id
    except Exception as e:
        if conn:
            conn.rollback()
        logger.exception("Erro ao salvar pagamento no banco: %s", e)
        raise
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


def criar_checkout_pagbank(presente, comprador, valor):
    reference_id = montar_reference_id(presente["id"], comprador["email"])
    telefone = normalizar_telefone(comprador.get("telefone"))
    public_base_url = get_public_base_url()
    webhook_url = f"{public_base_url}/webhook/pagbank"
    valor_centavos = valor_em_centavos(valor)

    customer = {
        "name": comprador["nome"],
        "email": comprador["email"],
    }
    if len(telefone) >= 10:
        customer["phones"] = [
            {
                "country": "55",
                "area": telefone[:2],
                "number": telefone[2:],
                "type": "MOBILE",
            }
        ]

    payload = {
        "reference_id": reference_id,
        "customer": customer,
        "items": [
            {
                "reference_id": str(presente["id"]),
                "name": presente["titulo"][:100],
                "quantity": 1,
                "unit_amount": valor_centavos,
            }
        ],
        "redirect_url": f"{public_base_url}/pagamento/sucesso",
        "return_url": f"{public_base_url}/pagamento/pendente",
        "notification_urls": [webhook_url],
        "payment_notification_urls": [webhook_url],
    }

    response = requests.post(
        f"{PAGBANK_API_URL}/checkouts",
        headers=get_pagbank_headers("criar_checkout"),
        json=payload,
        timeout=20,
    )

    if response.status_code not in (200, 201):
        logger.error(
            "Erro PagBank ao criar checkout: status=%s, resposta=%s",
            response.status_code,
            response.text[:500],
        )
        raise RuntimeError("Nao foi possivel iniciar o pagamento. Tente novamente.")

    checkout = response.json()
    checkout_url = extrair_checkout_url_pagbank(checkout)
    if not checkout.get("id") or not checkout_url:
        logger.error("Resposta PagBank sem checkout id ou link PAY: %s", checkout)
        raise RuntimeError("Nao foi possivel iniciar o pagamento. Tente novamente.")

    return {
        "checkout_id": checkout["id"],
        "checkout_url": checkout_url,
        "reference_id": reference_id,
    }


def criar_pagamento_pagbank(
    presente_id,
    nome_pagador,
    email_pagador,
    telefone_pagador,
    mensagem_pagador,
):
    """Cria um checkout PagBank para um presente."""
    if not presente_id or not nome_pagador or not email_pagador:
        logger.warning("Dados incompletos para criar pagamento")
        return {
            "sucesso": False,
            "erro": "Nome, email e presente sao obrigatorios",
        }

    presente = get_presente_by_id(presente_id)
    if not presente:
        logger.warning("Presente %s nao encontrado", presente_id)
        return {
            "sucesso": False,
            "erro": "Presente nao encontrado",
        }

    if presente.get("status") == "indisponivel":
        logger.warning("Tentativa de pagamento para presente indisponivel: %s", presente_id)
        return {
            "sucesso": False,
            "erro": "Este presente esta indisponivel no momento",
        }

    if PAGBANK_SELLER_EMAIL and email_pagador.lower() == PAGBANK_SELLER_EMAIL:
        logger.warning("Tentativa de pagamento com o mesmo email configurado para o vendedor")
        return {
            "sucesso": False,
            "erro": "Use uma conta PagBank diferente da conta do vendedor para concluir o pagamento.",
        }

    try:
        valor = float(presente["valor_sugerido"])
        comprador = {
            "nome": nome_pagador,
            "email": email_pagador,
            "telefone": telefone_pagador,
        }
        checkout = criar_checkout_pagbank(presente, comprador, valor)

        try:
            pagamento_id = salvar_pagamento_no_banco(
                presente_id,
                nome_pagador,
                email_pagador,
                telefone_pagador,
                mensagem_pagador,
                valor,
                checkout["reference_id"],
                checkout["checkout_url"],
            )
        except Exception as e:
            return {
                "sucesso": False,
                "erro": str(e),
                "tipo_erro": "salvar_pagamento",
            }

        logger.info(
            "Pagamento PagBank criado: ID %s, Checkout %s",
            pagamento_id,
            checkout["checkout_id"],
        )
        return {
            "sucesso": True,
            "checkout_url": checkout["checkout_url"],
            "checkout_id": checkout["checkout_id"],
            "reference_id": checkout["reference_id"],
            "pagamento_id": pagamento_id,
        }
    except RuntimeError as e:
        logger.error("Erro PagBank: %s", e)
        return {
            "sucesso": False,
            "erro": str(e),
            "tipo_erro": "pagbank",
        }
    except Exception as e:
        logger.error("Erro ao criar checkout PagBank: %s", e, exc_info=True)
        return {
            "sucesso": False,
            "erro": "Nao foi possivel iniciar o pagamento. Tente novamente.",
        }


def atualizar_status_presente(presente_id, novo_status):
    """Atualiza o status de um presente no banco de dados."""
    conn = None
    cur = None

    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE presentes
            SET status = %s, updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
            """,
            (novo_status, presente_id),
        )
        conn.commit()
        logger.info("Presente %s atualizado para status: %s", presente_id, novo_status)
        return True
    except psycopg2.Error as e:
        logger.error("Erro ao atualizar status do presente %s: %s", presente_id, e)
        if conn:
            conn.rollback()
        return False
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


def atualizar_pagamento_status(preferencia_id, mercado_pago_id, novo_status, metodo=None):
    """Atualiza o status de um pagamento no banco de dados."""
    conn = None
    cur = None
    mercado_pago_id_num = None
    if mercado_pago_id is not None:
        try:
            mercado_pago_id_num = int(mercado_pago_id)
        except (TypeError, ValueError):
            mercado_pago_id_num = None

    try:
        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        if mercado_pago_id_num is None:
            cur.execute(
                """
                UPDATE pagamentos_mercado_pago
                SET status = %s, metodo_pagamento = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE preferencia_id = %s
                RETURNING presente_id
                """,
                (novo_status, metodo or "desconhecido", preferencia_id),
            )
        else:
            cur.execute(
                """
                UPDATE pagamentos_mercado_pago
                SET status = %s, mercado_pago_id = %s, metodo_pagamento = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE preferencia_id = %s
                RETURNING presente_id
                """,
                (novo_status, mercado_pago_id_num, metodo or "desconhecido", preferencia_id),
            )
        resultado = cur.fetchone()
        conn.commit()

        if resultado:
            return {"presente_id": resultado["presente_id"]}

        logger.warning("Pagamento com preferencia_id %s nao encontrado", preferencia_id)
        return {}
    except psycopg2.Error as e:
        logger.error("Erro ao atualizar pagamento %s: %s", preferencia_id, e)
        if conn:
            conn.rollback()
        return {}
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


def registrar_webhook_log(mercado_pago_id, tipo_notificacao, status, dados_json, erro=None):
    """Registra uma notificacao de webhook para auditoria e debugging."""
    conn = None
    cur = None
    mercado_pago_id_num = None
    if mercado_pago_id is not None:
        try:
            mercado_pago_id_num = int(mercado_pago_id)
        except (TypeError, ValueError):
            mercado_pago_id_num = None

    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO webhook_logs
            (mercado_pago_id, tipo_notificacao, status, dados_json, erro)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                mercado_pago_id_num,
                tipo_notificacao,
                status,
                json.dumps(dados_json),
                erro,
            ),
        )
        conn.commit()
        logger.info("Webhook registrado: ID externo %s, Tipo %s", mercado_pago_id, tipo_notificacao)
    except psycopg2.Error as e:
        logger.error("Erro ao registrar webhook log: %s", e)
        if conn:
            conn.rollback()
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


def mapear_status_pagbank(status):
    status_normalizado = (status or "").upper()
    if status_normalizado in {"PAID", "AUTHORIZED", "APPROVED", "CAPTURED"}:
        return "approved"
    if status_normalizado in {"WAITING", "IN_ANALYSIS", "PENDING", "ACTIVE"}:
        return "pending"
    if status_normalizado in {"CANCELED", "CANCELLED", "DECLINED", "VOIDED", "EXPIRED"}:
        return "cancelled"
    if status_normalizado in {"DENIED", "REJECTED"}:
        return "rejected"
    return "pending"


def extrair_dados_webhook_pagbank(data):
    charges = data.get("charges") or []
    charge = charges[0] if charges else {}
    payment_method = charge.get("payment_method") or {}

    checkout_id = (
        data.get("reference_id")
        or charge.get("reference_id")
        or data.get("checkout_id")
        or data.get("id")
    )
    status = (
        charge.get("status")
        or data.get("status")
        or data.get("event")
        or data.get("type")
    )
    pagamento_id = charge.get("id") or data.get("payment_id") or data.get("id")
    metodo = payment_method.get("type") or data.get("payment_method") or "desconhecido"

    return {
        "checkout_id": checkout_id,
        "pagamento_id": pagamento_id,
        "status_original": status,
        "status": mapear_status_pagbank(status),
        "metodo": metodo,
    }


@pagamentos_bp.route("/api/presentear", methods=["POST"])
def criar_pagamento():
    """Cria um link de pagamento no PagBank para um presente."""
    try:
        data = request.get_json(silent=True)
        if not data:
            return jsonify({"sucesso": False, "erro": "Dados JSON invalidos"}), 400

        presente_id = data.get("presente_id")
        nome_pagador = data.get("nome_pagador", "").strip()
        email_pagador = data.get("email_pagador", "").strip()
        telefone_pagador = data.get("telefone_pagador", "").strip()
        mensagem_pagador = data.get("mensagem_pagador", "").strip()

        if not presente_id:
            return jsonify({"sucesso": False, "erro": "Presente e obrigatorio"}), 400

        if not nome_pagador:
            return jsonify({"sucesso": False, "erro": "Nome do pagador e obrigatorio"}), 400

        if not email_pagador or "@" not in email_pagador:
            return jsonify({"sucesso": False, "erro": "Email valido e obrigatorio"}), 400

        if not telefone_pagador:
            return jsonify({"sucesso": False, "erro": "Telefone e obrigatorio"}), 400

        resultado = criar_pagamento_pagbank(
            int(presente_id),
            nome_pagador,
            email_pagador,
            telefone_pagador,
            mensagem_pagador,
        )

        if not resultado.get("sucesso"):
            if resultado.get("tipo_erro") == "salvar_pagamento":
                return jsonify({"erro": resultado.get("erro", "Erro ao salvar pagamento")}), 500

            if resultado.get("tipo_erro") == "pagbank":
                return jsonify(resultado), 500

            status_code = 404 if "nao encontrado" in resultado.get("erro", "").lower() else 400
            return jsonify(resultado), status_code

        logger.info("Pagamento criado com sucesso: Presente %s, Email %s", presente_id, email_pagador)
        return jsonify({"sucesso": True, "checkout_url": resultado["checkout_url"]}), 200
    except Exception as e:
        logger.error("Erro ao criar pagamento: %s", e, exc_info=True)
        return jsonify({"erro": str(e)}), 500


@pagamentos_bp.route("/webhook/pagbank", methods=["POST"])
def webhook_pagbank():
    """Webhook para receber notificacoes de checkout/pagamento do PagBank."""
    try:
        data = request.get_json(silent=True) or {}
        if not isinstance(data, dict):
            logger.warning("Webhook PagBank ignorado: payload invalido")
            return jsonify({"recebido": False, "erro": "Payload invalido"}), 400

        dados_pagbank = extrair_dados_webhook_pagbank(data)
        tipo_notificacao = data.get("type") or data.get("event") or "pagbank"
        checkout_id = dados_pagbank["checkout_id"]
        pagamento_id = dados_pagbank["pagamento_id"]
        status_pagamento = dados_pagbank["status"]

        logger.info(
            "Webhook PagBank recebido: Tipo %s, Checkout %s, Status %s",
            tipo_notificacao,
            checkout_id,
            dados_pagbank["status_original"],
        )

        registrar_webhook_log(pagamento_id, tipo_notificacao, "recebido", data)

        if not checkout_id or not dados_pagbank["status_original"]:
            registrar_webhook_log(
                pagamento_id,
                tipo_notificacao,
                "erro_payload",
                data,
                "Webhook PagBank sem checkout_id ou status",
            )
            logger.warning("Webhook PagBank sem checkout_id ou status")
            return jsonify({"recebido": False, "erro": "Evento invalido"}), 400

        resultado_update = atualizar_pagamento_status(
            checkout_id,
            pagamento_id,
            status_pagamento,
            dados_pagbank["metodo"],
        )
        presente_id = resultado_update.get("presente_id")

        if status_pagamento == "approved" and presente_id:
            sucesso = atualizar_status_presente(presente_id, "indisponivel")
            if sucesso:
                logger.info(
                    "Presente %s marcado como indisponivel (pagamento aprovado)",
                    presente_id,
                )
                registrar_webhook_log(
                    pagamento_id,
                    tipo_notificacao,
                    "processado",
                    data,
                )
            else:
                logger.error("Erro ao atualizar presente %s para indisponivel", presente_id)
                registrar_webhook_log(
                    pagamento_id,
                    tipo_notificacao,
                    "erro_update_presente",
                    data,
                    f"Erro ao atualizar presente {presente_id}",
                )
        elif status_pagamento in ["cancelled", "rejected"] and presente_id:
            sucesso = atualizar_status_presente(presente_id, "disponivel")
            if sucesso:
                logger.info(
                    "Presente %s marcado como disponivel (pagamento %s)",
                    presente_id,
                    status_pagamento,
                )
            else:
                logger.error("Erro ao atualizar presente %s para disponivel", presente_id)

        return jsonify({"recebido": True}), 200
    except Exception as e:
        logger.error("Erro ao processar webhook: %s", e, exc_info=True)
        return jsonify({"recebido": False, "erro": str(e)}), 500


@pagamentos_bp.route("/pagamento/sucesso", methods=["GET"])
def pagamento_sucesso():
    return render_template("pagamento_sucesso.html"), 200


@pagamentos_bp.route("/pagamento/falha", methods=["GET"])
def pagamento_falha():
    return render_template("pagamento_falha.html"), 200


@pagamentos_bp.route("/pagamento/pendente", methods=["GET"])
def pagamento_pendente():
    return render_template("pagamento_pendente.html"), 200


@pagamentos_bp.route("/api/status_pagamento/<int:presente_id>", methods=["GET"])
def status_pagamento_endpoint(presente_id):
    """Retorna o status de pagamento de um presente."""
    conn = None
    cur = None

    try:
        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(
            """
            SELECT status FROM presentes WHERE id = %s
            """,
            (presente_id,),
        )
        resultado = cur.fetchone()

        if not resultado:
            return jsonify({"erro": "Presente nao encontrado"}), 404

        return jsonify({"presente_id": presente_id, "status": resultado["status"]}), 200
    except psycopg2.Error as e:
        logger.error("Erro ao consultar status do presente %s: %s", presente_id, e)
        return jsonify({"erro": "Erro ao consultar status"}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()
