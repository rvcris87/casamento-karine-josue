"""
Integracao com InfinitePay para pagamento de presentes.
Gera links do Checkout Integrado e processa notificacoes por webhook.
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

INFINITEPAY_API_URL = os.getenv(
    "INFINITEPAY_API_URL",
    "https://api.checkout.infinitepay.io",
).rstrip("/")
INFINITEPAY_HANDLE = os.getenv("INFINITEPAY_HANDLE", "").strip().lstrip("$")

pagamentos_bp = Blueprint("pagamentos", __name__)


def get_infinitepay_headers():
    return {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


logger.info("InfinitePay handle configurado: %s", "sim" if INFINITEPAY_HANDLE else "nao")


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
    for row in rows:
        if isinstance(row, dict):
            table_name = row["table_name"]
            column_name = row["column_name"]
        else:
            table_name, column_name = row
        tables.setdefault(table_name, set()).add(column_name)

    if "pagamentos_presentes" in tables:
        return {"table": "pagamentos_presentes", "columns": tables["pagamentos_presentes"]}

    if "pagamentos_mercado_pago" in tables:
        return {"table": "pagamentos_mercado_pago", "columns": tables["pagamentos_mercado_pago"]}

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


def montar_reference_id(presente_id, pagamento_id):
    referencia = f"presente-{presente_id}-pagamento-{pagamento_id}"
    return referencia[:64]


def extrair_ids_do_order_nsu(order_nsu):
    partes = (order_nsu or "").split("-")
    ids = {"presente_id": None, "pagamento_id": None}
    if len(partes) >= 4 and partes[0] == "presente" and partes[2] == "pagamento":
        try:
            ids["presente_id"] = int(partes[1])
            ids["pagamento_id"] = int(partes[3])
        except (TypeError, ValueError):
            return ids
    return ids


def buscar_campo_recursivo(data, nomes):
    if isinstance(nomes, str):
        nomes = {nomes}
    else:
        nomes = set(nomes)

    if isinstance(data, dict):
        for nome in nomes:
            if nome in data and data[nome] not in (None, ""):
                return data[nome]

        for valor in data.values():
            encontrado = buscar_campo_recursivo(valor, nomes)
            if encontrado not in (None, ""):
                return encontrado

    if isinstance(data, list):
        for item in data:
            encontrado = buscar_campo_recursivo(item, nomes)
            if encontrado not in (None, ""):
                return encontrado

    return None


def extrair_checkout_url_infinitepay(checkout):
    """Extrai o link de checkout aceitando formatos comuns de resposta da API."""
    if isinstance(checkout, str) and checkout.startswith("http"):
        return checkout

    if not isinstance(checkout, dict):
        return None

    for chave in ("url", "link", "checkout_url", "payment_url", "invoice_url"):
        valor = checkout.get(chave)
        if isinstance(valor, str) and valor.startswith("http"):
            return valor

    for chave in ("data", "checkout", "invoice"):
        valor = checkout.get(chave)
        if isinstance(valor, dict):
            url = extrair_checkout_url_infinitepay(valor)
            if url:
                return url

    for link in checkout.get("links", []) or []:
        if isinstance(link, dict):
            href = link.get("href") or link.get("url")
            if isinstance(href, str) and href.startswith("http"):
                return href

    return None


def get_public_base_url():
    base_url = os.getenv(
        "BASE_URL",
        "https://karine-josue-production.up.railway.app",
    ).strip().rstrip("/")
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
    preferencia_id=None,
    init_point=None,
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
        logger.info(
            "Pagamento salvo: tabela=%s, pagamento_id=%s, presente_id=%s, status=iniciado",
            table_config["table"],
            pagamento_id,
            presente_id,
        )
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


def atualizar_checkout_pagamento(pagamento_id, order_nsu, checkout_url):
    """Grava a referencia InfinitePay no pagamento quando a tabela suporta esses campos."""
    conn = None
    cur = None

    try:
        conn = get_connection()
        cur = conn.cursor()
        table_config = get_pagamentos_table_config(cur)

        if table_config["table"] == "pagamentos_mercado_pago":
            cur.execute(
                """
                UPDATE pagamentos_mercado_pago
                SET preferencia_id = %s, init_point = %s, updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
                """,
                (order_nsu, checkout_url, pagamento_id),
            )

        conn.commit()
    except Exception as e:
        if conn:
            conn.rollback()
        logger.warning("Nao foi possivel gravar checkout InfinitePay no pagamento %s: %s", pagamento_id, e)
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


def criar_checkout_infinitepay(presente, comprador, valor, order_nsu):
    telefone = normalizar_telefone(comprador.get("telefone"))
    public_base_url = get_public_base_url()
    webhook_url = f"{public_base_url}/webhook/infinitepay"
    valor_centavos = valor_em_centavos(valor)

    customer = {
        "name": comprador["nome"],
        "email": comprador["email"],
    }
    if len(telefone) >= 10:
        customer["phone_number"] = f"+55{telefone}"

    payload = {
        "handle": INFINITEPAY_HANDLE,
        "order_nsu": order_nsu,
        "redirect_url": f"{public_base_url}/pagamento/sucesso",
        "webhook_url": webhook_url,
        "items": [
            {
                "quantity": 1,
                "price": valor_centavos,
                "description": presente["titulo"][:100],
            }
        ],
        "customer": customer,
    }

    logger.debug(
        "Payload InfinitePay /links: order_nsu=%s, valor_centavos=%s, item=%s",
        order_nsu,
        valor_centavos,
        presente["titulo"][:100],
    )

    response = requests.post(
        f"{INFINITEPAY_API_URL}/links",
        headers=get_infinitepay_headers(),
        json=payload,
        timeout=20,
    )

    if response.status_code not in (200, 201):
        logger.error(
            "Erro InfinitePay ao criar checkout: status=%s, resposta=%s",
            response.status_code,
            response.text[:500],
        )
        raise RuntimeError("Nao foi possivel iniciar o pagamento. Tente novamente.")

    checkout = response.json()
    logger.debug("Resposta InfinitePay /links: %s", checkout)
    checkout_url = extrair_checkout_url_infinitepay(checkout)
    if not checkout_url:
        logger.error("Resposta InfinitePay sem URL de checkout. Chaves: %s", list(checkout.keys()))
        logger.debug("Resposta completa InfinitePay sem URL: %s", checkout)
        raise RuntimeError("Nao foi possivel iniciar o pagamento. Tente novamente.")

    return {
        "checkout_id": checkout.get("id") or checkout.get("slug") or order_nsu,
        "checkout_url": checkout_url,
        "reference_id": order_nsu,
    }


def consultar_pagamento_infinitepay(order_nsu, transaction_nsu, slug):
    if not (INFINITEPAY_HANDLE and order_nsu and transaction_nsu and slug):
        return None

    payload = {
        "handle": INFINITEPAY_HANDLE,
        "order_nsu": order_nsu,
        "transaction_nsu": transaction_nsu,
        "slug": slug,
    }

    response = requests.post(
        f"{INFINITEPAY_API_URL}/payment_check",
        headers=get_infinitepay_headers(),
        json=payload,
        timeout=10,
    )
    logger.debug("Resposta InfinitePay /payment_check: order_nsu=%s, resposta=%s", order_nsu, response.text[:500])
    if response.status_code not in (200, 201):
        logger.warning(
            "Consulta InfinitePay falhou: status=%s, order_nsu=%s",
            response.status_code,
            order_nsu,
        )
        return None

    return response.json()


def criar_pagamento_infinitepay(
    presente_id,
    nome_pagador,
    email_pagador,
    telefone_pagador,
    mensagem_pagador,
):
    """Cria um checkout InfinitePay para um presente."""
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

    if presente.get("status") != "disponivel":
        logger.warning(
            "Tentativa de pagamento bloqueada: presente_id=%s, status=%s",
            presente_id,
            presente.get("status"),
        )
        return {
            "sucesso": False,
            "erro": "Este presente esta indisponivel no momento",
        }

    if not INFINITEPAY_HANDLE:
        logger.error("INFINITEPAY_HANDLE nao configurado")
        return {
            "sucesso": False,
            "erro": "Pagamento indisponivel no momento. InfinitePay nao configurada.",
            "tipo_erro": "infinitepay_config",
        }

    try:
        valor = float(presente["valor_sugerido"])
        comprador = {
            "nome": nome_pagador,
            "email": email_pagador,
            "telefone": telefone_pagador,
        }

        try:
            pagamento_id = salvar_pagamento_no_banco(
                presente_id,
                nome_pagador,
                email_pagador,
                telefone_pagador,
                mensagem_pagador,
                valor,
            )
        except Exception as e:
            return {
                "sucesso": False,
                "erro": str(e),
                "tipo_erro": "salvar_pagamento",
            }

        order_nsu = montar_reference_id(presente_id, pagamento_id)
        checkout = criar_checkout_infinitepay(presente, comprador, valor, order_nsu)
        atualizar_checkout_pagamento(pagamento_id, checkout["reference_id"], checkout["checkout_url"])

        logger.info(
            "Pagamento InfinitePay criado: ID interno %s, order_nsu %s",
            pagamento_id,
            checkout["reference_id"],
        )
        return {
            "sucesso": True,
            "checkout_url": checkout["checkout_url"],
            "checkout_id": checkout["checkout_id"],
            "reference_id": checkout["reference_id"],
            "pagamento_id": pagamento_id,
        }
    except RuntimeError as e:
        logger.error("Erro InfinitePay: %s", e)
        return {
            "sucesso": False,
            "erro": str(e),
            "tipo_erro": "infinitepay",
        }
    except Exception as e:
        logger.error("Erro ao criar checkout InfinitePay: %s", e, exc_info=True)
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
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = 'presentes'
              AND column_name IN ('status', 'updated_at')
            """
        )
        colunas = {row[0] for row in cur.fetchall()}
        if "status" not in colunas:
            logger.error("Coluna status nao encontrada na tabela presentes")
            return False

        if "updated_at" in colunas:
            cur.execute(
                """
                UPDATE presentes
                SET status = %s, updated_at = NOW()
                WHERE id = %s
                """,
                (novo_status, presente_id),
            )
        else:
            cur.execute(
                """
                UPDATE presentes
                SET status = %s
                WHERE id = %s
                """,
                (novo_status, presente_id),
            )

        conn.commit()
        if cur.rowcount == 0:
            logger.error("Nenhum presente encontrado para atualizar: presente_id=%s", presente_id)
            return False

        logger.info("Presente marcado como %s: presente_id=%s", novo_status, presente_id)
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
    ids_order_nsu = extrair_ids_do_order_nsu(preferencia_id)
    mercado_pago_id_num = None
    if mercado_pago_id is not None:
        try:
            mercado_pago_id_num = int(mercado_pago_id)
        except (TypeError, ValueError):
            mercado_pago_id_num = None

    try:
        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        table_config = get_pagamentos_table_config(cur)

        if table_config["table"] == "pagamentos_presentes":
            cur.execute(
                """
                UPDATE pagamentos_presentes
                SET status_pagamento = %s
                WHERE id = %s
                RETURNING presente_id
                """,
                (novo_status, ids_order_nsu["pagamento_id"]),
            )
        else:
            if mercado_pago_id_num is None:
                cur.execute(
                    """
                    UPDATE pagamentos_mercado_pago
                    SET status = %s, metodo_pagamento = %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE preferencia_id = %s OR id = %s OR init_point ILIKE %s
                    RETURNING presente_id
                    """,
                    (
                        novo_status,
                        metodo or "desconhecido",
                        preferencia_id,
                        ids_order_nsu["pagamento_id"],
                        f"%{preferencia_id}%",
                    ),
                )
            else:
                cur.execute(
                    """
                    UPDATE pagamentos_mercado_pago
                    SET status = %s, mercado_pago_id = %s, metodo_pagamento = %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE preferencia_id = %s
                       OR id = %s
                       OR mercado_pago_id = %s
                       OR init_point ILIKE %s
                    RETURNING presente_id
                    """,
                    (
                        novo_status,
                        mercado_pago_id_num,
                        metodo or "desconhecido",
                        preferencia_id,
                        ids_order_nsu["pagamento_id"],
                        mercado_pago_id_num,
                        f"%{preferencia_id}%",
                    ),
                )
        resultado = cur.fetchone()
        conn.commit()

        if resultado:
            logger.info(
                "Pagamento atualizado: referencia=%s, status=%s, presente_id=%s",
                preferencia_id,
                novo_status,
                resultado["presente_id"],
            )
            return {"presente_id": resultado["presente_id"]}

        if ids_order_nsu["presente_id"]:
            logger.warning(
                "Pagamento nao encontrado pela referencia %s, usando presente_id extraido do order_nsu: %s",
                preferencia_id,
                ids_order_nsu["presente_id"],
            )
            return {"presente_id": ids_order_nsu["presente_id"]}

        logger.warning("Pagamento com referencia %s nao encontrado", preferencia_id)
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


def mapear_status_infinitepay(data):
    pago = buscar_campo_recursivo(data, {"paid", "is_paid", "paid_out"})
    if pago is True or str(pago).lower() == "true":
        return "approved"

    status = buscar_campo_recursivo(data, {"status", "event", "type", "payment_status"})
    status_normalizado = str(status or "").upper()
    if status_normalizado in {"PAID", "AUTHORIZED", "APPROVED", "CAPTURED", "SUCCESS", "COMPLETED", "CONCLUIDA"}:
        return "approved"
    if status_normalizado in {"WAITING", "IN_ANALYSIS", "PENDING", "ACTIVE"}:
        return "pending"
    if status_normalizado in {"CANCELED", "CANCELLED", "DECLINED", "VOIDED", "EXPIRED"}:
        return "cancelled"
    if status_normalizado in {"DENIED", "REJECTED"}:
        return "rejected"
    return "pending"


def extrair_dados_webhook_infinitepay(data):
    order_nsu = buscar_campo_recursivo(data, {
        "order_nsu",
        "orderNsu",
        "reference_id",
        "referenceId",
        "reference",
        "external_reference",
    })
    status = buscar_campo_recursivo(data, {"status", "event", "type", "payment_status"})
    transaction_nsu = buscar_campo_recursivo(data, {
        "transaction_nsu",
        "transactionNsu",
        "payment_id",
        "paymentId",
        "id",
    })
    slug = buscar_campo_recursivo(data, {"slug", "invoice_slug", "invoiceSlug", "checkout_slug"})
    pagamento_id = (
        transaction_nsu
        or slug
    )
    metodo = buscar_campo_recursivo(data, {"capture_method", "payment_method", "paymentMethod"}) or "desconhecido"

    return {
        "checkout_id": order_nsu or transaction_nsu or slug,
        "order_nsu": order_nsu,
        "pagamento_id": pagamento_id,
        "status_original": status,
        "status": mapear_status_infinitepay(data),
        "metodo": metodo,
        "transaction_nsu": transaction_nsu,
        "slug": slug,
    }


@pagamentos_bp.route("/api/presentear", methods=["POST"])
def criar_pagamento():
    """Cria um link de pagamento na InfinitePay para um presente."""
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

        resultado = criar_pagamento_infinitepay(
            int(presente_id),
            nome_pagador,
            email_pagador,
            telefone_pagador,
            mensagem_pagador,
        )

        if not resultado.get("sucesso"):
            if resultado.get("tipo_erro") == "salvar_pagamento":
                return jsonify({"erro": resultado.get("erro", "Erro ao salvar pagamento")}), 500

            if resultado.get("tipo_erro") in {"infinitepay", "infinitepay_config"}:
                return jsonify(resultado), 500

            status_code = 404 if "nao encontrado" in resultado.get("erro", "").lower() else 400
            return jsonify(resultado), status_code

        logger.info("Pagamento criado com sucesso: Presente %s, Email %s", presente_id, email_pagador)
        return jsonify({"sucesso": True, "checkout_url": resultado["checkout_url"]}), 200
    except Exception as e:
        logger.error("Erro ao criar pagamento: %s", e, exc_info=True)
        return jsonify({"erro": str(e)}), 500


@pagamentos_bp.route("/webhook/infinitepay", methods=["POST"])
def webhook_infinitepay():
    """Webhook para receber notificacoes de checkout/pagamento da InfinitePay."""
    try:
        data = request.get_json(silent=True) or {}
        if not isinstance(data, dict):
            logger.warning("Webhook InfinitePay ignorado: payload invalido")
            return jsonify({"recebido": False, "erro": "Payload invalido"}), 400

        dados_infinitepay = extrair_dados_webhook_infinitepay(data)
        tipo_notificacao = data.get("type") or data.get("event") or "infinitepay"
        checkout_id = dados_infinitepay["checkout_id"]
        pagamento_id = dados_infinitepay["pagamento_id"]
        status_pagamento = dados_infinitepay["status"]

        if (
            status_pagamento != "approved"
            and dados_infinitepay["order_nsu"]
            and dados_infinitepay["transaction_nsu"]
            and dados_infinitepay["slug"]
        ):
            consulta = consultar_pagamento_infinitepay(
                dados_infinitepay["order_nsu"],
                dados_infinitepay["transaction_nsu"],
                dados_infinitepay["slug"],
            )
            if consulta:
                status_pagamento = mapear_status_infinitepay(consulta)
                dados_infinitepay["metodo"] = consulta.get("capture_method") or dados_infinitepay["metodo"]
                logger.info("Status InfinitePay confirmado via payment_check: order_nsu=%s", checkout_id)

        logger.info(
            "Webhook InfinitePay recebido: Tipo %s, order_nsu %s, Status %s",
            tipo_notificacao,
            checkout_id,
            dados_infinitepay["status_original"] or status_pagamento,
        )

        registrar_webhook_log(pagamento_id, tipo_notificacao, "recebido", data)

        if not checkout_id:
            registrar_webhook_log(
                pagamento_id,
                tipo_notificacao,
                "erro_payload",
                data,
                "Webhook InfinitePay sem order_nsu",
            )
            logger.warning("Webhook InfinitePay sem order_nsu")
            return jsonify({"recebido": False, "erro": "Evento invalido"}), 400

        resultado_update = atualizar_pagamento_status(
            checkout_id,
            pagamento_id,
            status_pagamento,
            dados_infinitepay["metodo"],
        )
        presente_id = resultado_update.get("presente_id")

        if status_pagamento == "approved" and presente_id:
            logger.info(
                "Pagamento aprovado recebido: referencia=%s, pagamento_id=%s",
                checkout_id,
                pagamento_id,
            )
            logger.info("Presente_id encontrado para pagamento aprovado: %s", presente_id)
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
        elif status_pagamento == "approved":
            logger.error(
                "Pagamento aprovado sem presente_id: referencia=%s, pagamento_id=%s",
                checkout_id,
                pagamento_id,
            )
            registrar_webhook_log(
                pagamento_id,
                tipo_notificacao,
                "erro_presente_id",
                data,
                "Pagamento aprovado sem presente_id",
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
    order_nsu = request.args.get("order_nsu")
    transaction_nsu = request.args.get("transaction_nsu")
    slug = request.args.get("slug")

    if order_nsu and transaction_nsu and slug:
        try:
            resultado = consultar_pagamento_infinitepay(order_nsu, transaction_nsu, slug)
            if resultado and resultado.get("paid") is True:
                update = atualizar_pagamento_status(
                    order_nsu,
                    transaction_nsu,
                    "approved",
                    resultado.get("capture_method"),
                )
                presente_id = update.get("presente_id")
                if presente_id:
                    atualizar_status_presente(presente_id, "indisponivel")
                    logger.info("Pagamento InfinitePay confirmado no retorno: order_nsu=%s", order_nsu)
        except Exception as e:
            logger.warning("Nao foi possivel confirmar pagamento no retorno InfinitePay: %s", e)

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
