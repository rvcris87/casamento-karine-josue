"""
Integracao com Mercado Pago para pagamento de presentes.
Suporta PIX, cartao de credito e debito.
"""

import json
import logging
import os
import time

import mercadopago
import psycopg2
from dotenv import load_dotenv
from flask import Blueprint, jsonify, render_template, request
from psycopg2.extras import RealDictCursor

from db import get_connection

load_dotenv()

logger = logging.getLogger(__name__)

MERCADO_PAGO_ACCESS_TOKEN = os.getenv("MERCADO_PAGO_ACCESS_TOKEN")
BASE_URL = os.getenv("BASE_URL", "http://localhost:5000")

sdk = mercadopago.SDK(MERCADO_PAGO_ACCESS_TOKEN)
pagamentos_bp = Blueprint("pagamentos", __name__)


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


def gerar_mercado_pago_id_temporario():
    """Gera um ID temporario unico antes do webhook devolver o ID real."""
    return -int(time.time_ns())


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
                    gerar_mercado_pago_id_temporario(),
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


def criar_pagamento_mercado_pago(
    presente_id,
    nome_pagador,
    email_pagador,
    telefone_pagador,
    mensagem_pagador,
):
    """Cria uma preferencia de pagamento no Mercado Pago para um presente."""
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
        logger.warning("Presente %s ja foi presenteado", presente_id)
        return {
            "sucesso": False,
            "erro": "Este presente ja foi presenteado",
        }

    try:
        valor = float(presente["valor_sugerido"])
        preference = {
            "items": [
                {
                    "title": presente["titulo"],
                    "description": presente["descricao"][:100] if presente["descricao"] else "",
                    "quantity": 1,
                    "currency_id": "BRL",
                    "unit_price": valor,
                }
            ],
            "payer": {
                "name": nome_pagador,
                "email": email_pagador,
                "phone": {"number": telefone_pagador},
            },
            "back_urls": {
                "success": f"{BASE_URL}/pagamento/sucesso",
                "failure": f"{BASE_URL}/pagamento/falha",
                "pending": f"{BASE_URL}/pagamento/pendente",
            },
            "notification_url": f"{BASE_URL}/webhook/mercado_pago",
            "external_reference": f"presente_{presente_id}_{email_pagador}",
            "auto_return": "all",
            "payment_methods": {
                "installments": 1,
            },
        }

        response = sdk.preference().create(preference)
        if response["status"] != 201:
            logger.error("Erro ao criar preferencia MP: %s", response)
            return {
                "sucesso": False,
                "erro": "Erro ao processar pagamento",
            }

        preference_data = response["response"]
        preferencia_id = preference_data["id"]
        init_point = preference_data["init_point"]

        try:
            pagamento_id = salvar_pagamento_no_banco(
                presente_id,
                nome_pagador,
                email_pagador,
                telefone_pagador,
                mensagem_pagador,
                valor,
                preferencia_id,
                init_point,
            )
        except Exception as e:
            return {
                "sucesso": False,
                "erro": str(e),
                "tipo_erro": "salvar_pagamento",
            }

        logger.info("Pagamento criado: ID %s, Preferencia MP %s", pagamento_id, preferencia_id)
        return {
            "sucesso": True,
            "init_point": init_point,
            "preferencia_id": preferencia_id,
            "pagamento_id": pagamento_id,
        }
    except Exception as e:
        logger.error("Erro ao criar preferencia Mercado Pago: %s", e, exc_info=True)
        return {
            "sucesso": False,
            "erro": "Erro ao processar pagamento",
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

    try:
        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(
            """
            UPDATE pagamentos_mercado_pago
            SET status = %s, mercado_pago_id = %s, metodo_pagamento = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE preferencia_id = %s
            RETURNING presente_id
            """,
            (novo_status, mercado_pago_id, metodo or "desconhecido", preferencia_id),
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
                mercado_pago_id,
                tipo_notificacao,
                status,
                json.dumps(dados_json),
                erro,
            ),
        )
        conn.commit()
        logger.info("Webhook registrado: MP ID %s, Tipo %s", mercado_pago_id, tipo_notificacao)
    except psycopg2.Error as e:
        logger.error("Erro ao registrar webhook log: %s", e)
        if conn:
            conn.rollback()
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


@pagamentos_bp.route("/api/presentear", methods=["POST"])
def criar_pagamento():
    """Cria um link de pagamento no Mercado Pago para um presente."""
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

        resultado = criar_pagamento_mercado_pago(
            int(presente_id),
            nome_pagador,
            email_pagador,
            telefone_pagador,
            mensagem_pagador,
        )

        if not resultado.get("sucesso"):
            if resultado.get("tipo_erro") == "salvar_pagamento":
                return jsonify({"erro": resultado.get("erro", "Erro ao salvar pagamento")}), 500

            status_code = 404 if "nao encontrado" in resultado.get("erro", "").lower() else 400
            return jsonify(resultado), status_code

        logger.info("Pagamento criado com sucesso: Presente %s, Email %s", presente_id, email_pagador)
        return jsonify({"sucesso": True, "checkout_url": resultado["init_point"]}), 200
    except Exception as e:
        logger.error("Erro ao criar pagamento: %s", e, exc_info=True)
        return jsonify({"erro": str(e)}), 500


@pagamentos_bp.route("/webhook/mercado_pago", methods=["POST"])
def webhook_mercado_pago():
    """Webhook para receber notificacoes de pagamento do Mercado Pago."""
    try:
        data = request.form if request.form else request.get_json()

        tipo_notificacao = data.get("type") or data.get("topic")
        mercado_pago_id = data.get("id")
        logger.info("Webhook recebido: Tipo %s, ID %s", tipo_notificacao, mercado_pago_id)

        registrar_webhook_log(
            mercado_pago_id,
            tipo_notificacao,
            "recebido",
            data.to_dict() if hasattr(data, "to_dict") else dict(data),
        )

        if tipo_notificacao != "payment":
            logger.warning("Notificacao ignorada: tipo %s", tipo_notificacao)
            return jsonify({"recebido": True}), 200

        payment_response = sdk.payment().get(mercado_pago_id)
        if payment_response["status"] != 200:
            logger.error("Erro ao consultar pagamento %s: %s", mercado_pago_id, payment_response)
            registrar_webhook_log(
                mercado_pago_id,
                tipo_notificacao,
                "erro_consulta",
                data.to_dict() if hasattr(data, "to_dict") else dict(data),
                "Erro ao consultar pagamento no MP",
            )
            return jsonify({"recebido": True}), 200

        payment = payment_response["response"]
        status_pagamento = payment.get("status")
        preferencia_id = payment.get("preference_id")
        metodo_pagamento = payment.get("payment_method", {}).get("type", "desconhecido")

        logger.info(
            "Pagamento %s: Status %s, Preferencia %s",
            mercado_pago_id,
            status_pagamento,
            preferencia_id,
        )

        resultado_update = atualizar_pagamento_status(
            preferencia_id,
            mercado_pago_id,
            status_pagamento,
            metodo_pagamento,
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
                    mercado_pago_id,
                    tipo_notificacao,
                    "processado",
                    data.to_dict() if hasattr(data, "to_dict") else dict(data),
                )
            else:
                logger.error("Erro ao atualizar presente %s para indisponivel", presente_id)
                registrar_webhook_log(
                    mercado_pago_id,
                    tipo_notificacao,
                    "erro_update_presente",
                    data.to_dict() if hasattr(data, "to_dict") else dict(data),
                    f"Erro ao atualizar presente {presente_id}",
                )
        elif status_pagamento in ["cancelled", "refunded"] and presente_id:
            sucesso = atualizar_status_presente(presente_id, "disponivel")
            if sucesso:
                logger.info(
                    "Presente %s marcado como disponivel (pagamento cancelado)",
                    presente_id,
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
