"""
Integração com Mercado Pago para pagamento de presentes.
Suporta PIX, cartão de crédito e débito.
"""

import os
import json
import logging
from flask import Blueprint, request, jsonify
from dotenv import load_dotenv
import mercadopago
import psycopg2
from psycopg2.extras import RealDictCursor
from db import get_connection

load_dotenv()

# Configuração de logging
logger = logging.getLogger(__name__)

# Credenciais do Mercado Pago (modo teste)
MERCADO_PAGO_ACCESS_TOKEN = os.getenv(
    "MERCADO_PAGO_ACCESS_TOKEN",
    "APP_USR-7108049560326594-042212-ee879f6a87885115519a5fed61ab8c04-3352130635"
)
MERCADO_PAGO_PUBLIC_KEY = os.getenv(
    "MERCADO_PAGO_PUBLIC_KEY",
    "APP_USR-583c2032-5036-4f0f-a2f8-c6cef74d0347"
)

# URL base para callbacks (será configurada em produção)
BASE_URL = os.getenv("BASE_URL", "http://localhost:5000")

# Inicializar SDK do Mercado Pago
sdk = mercadopago.SDK(os.getenv("MERCADO_PAGO_ACCESS_TOKEN"))

# Criar blueprint
pagamentos_bp = Blueprint("pagamentos", __name__)


def get_presente_by_id(presente_id):
    """
    Busca um presente no banco de dados pelo ID.
    
    Args:
        presente_id (int): ID do presente
        
    Returns:
        dict: Dados do presente ou None se não encontrado
    """
    conn = None
    cur = None
    
    try:
        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("""
            SELECT *
            FROM presentes
            WHERE id = %s
        """, (presente_id,))

        presente = cur.fetchone()
        logger.info(f"Resultado da busca do presente {presente_id}: {presente}")

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
        logger.error(f"Erro ao buscar presente {presente_id}: {e}")
        return None
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


def criar_pagamento_mercado_pago(presente_id, nome_pagador, email_pagador, 
                                  telefone_pagador, mensagem_pagador):
    """
    Cria uma preferência de pagamento no Mercado Pago para um presente.
    
    Args:
        presente_id (int): ID do presente
        nome_pagador (str): Nome de quem está presenteando
        email_pagador (str): Email de quem está presenteando
        telefone_pagador (str): Telefone de quem está presenteando
        mensagem_pagador (str): Mensagem opcional
        
    Returns:
        dict: Contém init_point (link de pagamento) e preferencia_id, ou erro
    """
    
    # Validações básicas
    if not presente_id or not nome_pagador or not email_pagador:
        logger.warning("Dados incompletos para criar pagamento")
        return {
            "sucesso": False,
            "erro": "Nome, email e presente são obrigatórios"
        }
    
    # Buscar presente no banco
    presente = get_presente_by_id(presente_id)
    
    if not presente:
        logger.warning(f"Presente {presente_id} não encontrado")
        return {
            "sucesso": False,
            "erro": "Presente não encontrado"
        }
    
    # Verificar se presente já foi presenteado
    if presente.get("status") == "indisponivel":
        logger.warning(f"Presente {presente_id} já foi presenteado")
        return {
            "sucesso": False,
            "erro": "Este presente já foi presenteado"
        }
    
    try:
        print("ID RECEBIDO:", presente_id)
        # Criar estrutura de preferência para Mercado Pago
        preference = {
            "items": [
                {
                    "title": presente["titulo"],
                    "description": presente["descricao"][:100] if presente["descricao"] else "",
                    "quantity": 1,
                    "currency_id": "BRL",
                    "unit_price": float(presente["valor_sugerido"])
                }
            ],
            "payer": {
                "name": nome_pagador,
                "email": email_pagador,
                "phone": {
                    "number": telefone_pagador
                }
            },
            "back_urls": {
                "success": f"{BASE_URL}/sucesso_pagamento",
                "failure": f"{BASE_URL}/falha_pagamento",
                "pending": f"{BASE_URL}/pagamento_pendente"
            },
            "notification_url": f"{BASE_URL}/webhook/mercado_pago",
            "external_reference": f"presente_{presente_id}_{email_pagador}",
            "auto_return": "approved",
            "payment_methods": {
                "excluded_payment_methods": [
                    {"id": "atm"}
                ],
                "excluded_payment_types": [
                    {"id": "atm"}
                ],
                "installments": 1  # Apenas pagamento à vista
            }
        }
        
        # Criar preferência no Mercado Pago
        response = sdk.preference().create(preference)
        
        if response["status"] != 201:
            logger.error(f"Erro ao criar preferência MP: {response}")
            return {
                "sucesso": False,
                "erro": "Erro ao processar pagamento"
            }
        
        preference_data = response["response"]
        preferencia_id = preference_data["id"]
        init_point = preference_data["init_point"]
        
        # Salvar informações do pagamento no banco (status = pending)
        conn = None
        cur = None
        
        try:
            conn = get_connection()
            cur = conn.cursor()
            
            cur.execute("""
                INSERT INTO pagamentos_mercado_pago 
                (presente_id, mercado_pago_id, status, valor, nome_pagador, 
                 email_pagador, telefone_pagador, mensagem_pagador, preferencia_id, init_point)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                presente_id,
                0,  # Será atualizado quando receber callback
                "pending",
                float(presente["valor_sugerido"]),
                nome_pagador,
                email_pagador,
                telefone_pagador,
                mensagem_pagador,
                preferencia_id,
                init_point
            ))
            
            pagamento_id = cur.fetchone()[0]
            conn.commit()
            
            logger.info(f"Pagamento criado: ID {pagamento_id}, Preferência MP {preferencia_id}")
            
            return {
                "sucesso": True,
                "init_point": init_point,
                "preferencia_id": preferencia_id,
                "pagamento_id": pagamento_id
            }
            
        except psycopg2.Error as e:
            logger.error(f"Erro ao salvar pagamento no banco: {e}")
            if conn:
                conn.rollback()
            return {
                "sucesso": False,
                "erro": "Erro ao salvar pagamento"
            }
        finally:
            if cur:
                cur.close()
            if conn:
                conn.close()
        
    except Exception as e:
        logger.error(f"Erro ao criar preferência Mercado Pago: {e}")
        return {
            "sucesso": False,
            "erro": "Erro ao processar pagamento"
        }


def atualizar_status_presente(presente_id, novo_status):
    """
    Atualiza o status de um presente no banco de dados.
    
    Args:
        presente_id (int): ID do presente
        novo_status (str): Novo status ('disponivel' ou 'indisponivel')
        
    Returns:
        bool: True se atualizado com sucesso, False caso contrário
    """
    conn = None
    cur = None
    
    try:
        conn = get_connection()
        cur = conn.cursor()
        
        cur.execute("""
            UPDATE presentes
            SET status = %s, updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
        """, (novo_status, presente_id))
        
        conn.commit()
        
        logger.info(f"Presente {presente_id} atualizado para status: {novo_status}")
        return True
        
    except psycopg2.Error as e:
        logger.error(f"Erro ao atualizar status do presente {presente_id}: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


def atualizar_pagamento_status(preferencia_id, mercado_pago_id, novo_status, metodo=None):
    """
    Atualiza o status de um pagamento no banco de dados.
    
    Args:
        preferencia_id (str): ID da preferência no Mercado Pago
        mercado_pago_id (int): ID do pagamento no Mercado Pago
        novo_status (str): Novo status (pending, approved, cancelled, refunded)
        metodo (str): Método de pagamento utilizado
        
    Returns:
        dict: Contém presente_id se atualizado com sucesso
    """
    conn = None
    cur = None
    
    try:
        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Atualizar pagamento
        cur.execute("""
            UPDATE pagamentos_mercado_pago
            SET status = %s, mercado_pago_id = %s, metodo_pagamento = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE preferencia_id = %s
            RETURNING presente_id
        """, (novo_status, mercado_pago_id, metodo or "desconhecido", preferencia_id))
        
        resultado = cur.fetchone()
        conn.commit()
        
        if resultado:
            return {"presente_id": resultado["presente_id"]}
        else:
            logger.warning(f"Pagamento com preferencia_id {preferencia_id} não encontrado")
            return {}
        
    except psycopg2.Error as e:
        logger.error(f"Erro ao atualizar pagamento {preferencia_id}: {e}")
        if conn:
            conn.rollback()
        return {}
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


def registrar_webhook_log(mercado_pago_id, tipo_notificacao, status, dados_json, erro=None):
    """
    Registra uma notificação de webhook para auditoria e debugging.
    
    Args:
        mercado_pago_id (int): ID do pagamento
        tipo_notificacao (str): Tipo de notificação (payment, plan, etc)
        status (str): Status da notificação
        dados_json (dict): Dados completos da notificação
        erro (str): Descrição de erro se houver
    """
    conn = None
    cur = None
    
    try:
        conn = get_connection()
        cur = conn.cursor()
        
        cur.execute("""
            INSERT INTO webhook_logs
            (mercado_pago_id, tipo_notificacao, status, dados_json, erro)
            VALUES (%s, %s, %s, %s, %s)
        """, (
            mercado_pago_id,
            tipo_notificacao,
            status,
            json.dumps(dados_json),
            erro
        ))
        
        conn.commit()
        logger.info(f"Webhook registrado: MP ID {mercado_pago_id}, Tipo {tipo_notificacao}")
        
    except psycopg2.Error as e:
        logger.error(f"Erro ao registrar webhook log: {e}")
        if conn:
            conn.rollback()
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


# ============================================================================
# ROTAS FLASK
# ============================================================================

@pagamentos_bp.route("/api/presentear", methods=["POST"])
def criar_pagamento():
    """
    Cria um link de pagamento no Mercado Pago para um presente.
    
    Recebe dados do pagador (nome, email, telefone, mensagem).
    Retorna o init_point (link de redirecionamento para pagamento).
    
    URL de uso no frontend:
        POST /criar_pagamento/<presente_id>
        Content-Type: application/json
        {
            "nome_pagador": "João Silva",
            "email_pagador": "joao@email.com",
            "telefone_pagador": "11999999999",
            "mensagem_pagador": "Mensagem opcional"
        }
    
    Respostas:
        200: {"sucesso": true, "init_point": "...", "preferencia_id": "..."}
        400: {"sucesso": false, "erro": "..."}
        404: {"sucesso": false, "erro": "Presente não encontrado"}
    """
    
    try:
        data = request.get_json(silent=True)
        
        if not data:
            return jsonify({
                "sucesso": False,
                "erro": "Dados JSON inválidos"
            }), 400
        
        presente_id = data.get("presente_id")
        print("ID RECEBIDO:", presente_id)
        nome_pagador = data.get("nome_pagador", "").strip()
        email_pagador = data.get("email_pagador", "").strip()
        telefone_pagador = data.get("telefone_pagador", "").strip()
        mensagem_pagador = data.get("mensagem_pagador", "").strip()

        if not presente_id:
            return jsonify({
                "sucesso": False,
                "erro": "Presente é obrigatório"
            }), 400
        
        # Validações
        if not nome_pagador:
            return jsonify({
                "sucesso": False,
                "erro": "Nome do pagador é obrigatório"
            }), 400
        
        if not email_pagador or "@" not in email_pagador:
            return jsonify({
                "sucesso": False,
                "erro": "Email válido é obrigatório"
            }), 400
        
        if not telefone_pagador:
            return jsonify({
                "sucesso": False,
                "erro": "Telefone é obrigatório"
            }), 400
        
        # Criar pagamento no Mercado Pago
        resultado = criar_pagamento_mercado_pago(
            int(presente_id),
            nome_pagador,
            email_pagador,
            telefone_pagador,
            mensagem_pagador
        )
        
        if not resultado.get("sucesso"):
            status_code = 404 if "não encontrado" in resultado.get("erro", "").lower() else 400
            return jsonify(resultado), status_code
        
        logger.info(f"Pagamento criado com sucesso: Presente {presente_id}, Email {email_pagador}")
        
        return jsonify({
            "sucesso": True,
            "checkout_url": resultado["init_point"]
        }), 200
        
    except Exception as e:
        print(f"Erro ao criar pagamento: {e}")
        logger.error(f"Erro ao criar pagamento: {e}", exc_info=True)
        return jsonify({
            "erro": str(e)
        }), 500


@pagamentos_bp.route("/webhook/mercado_pago", methods=["POST"])
def webhook_mercado_pago():
    """
    Webhook para receber notificações de pagamento do Mercado Pago.
    
    Mercado Pago envia notificações em dois formatos:
    1. IPN (Instant Payment Notification) - topic=payment
    2. Webhooks - topic=payment
    
    Atualiza o status do presente para "indisponivel" quando pagamento é aprovado.
    """
    
    try:
        # Mercado Pago envia a notificação como form data, não JSON
        data = request.form if request.form else request.get_json()
        
        tipo_notificacao = data.get("type") or data.get("topic")
        mercado_pago_id = data.get("id")
        
        logger.info(f"Webhook recebido: Tipo {tipo_notificacao}, ID {mercado_pago_id}")
        
        # Registrar webhook para auditoria
        registrar_webhook_log(
            mercado_pago_id,
            tipo_notificacao,
            "recebido",
            data.to_dict() if hasattr(data, 'to_dict') else dict(data)
        )
        
        # Processar apenas notificações de pagamento
        if tipo_notificacao != "payment":
            logger.warning(f"Notificação ignorada: tipo {tipo_notificacao}")
            return jsonify({"recebido": True}), 200
        
        # Buscar detalhes do pagamento no Mercado Pago
        payment_response = sdk.payment().get(mercado_pago_id)
        
        if payment_response["status"] != 200:
            logger.error(f"Erro ao consultar pagamento {mercado_pago_id}: {payment_response}")
            registrar_webhook_log(
                mercado_pago_id,
                tipo_notificacao,
                "erro_consulta",
                data.to_dict() if hasattr(data, 'to_dict') else dict(data),
                "Erro ao consultar pagamento no MP"
            )
            return jsonify({"recebido": True}), 200
        
        payment = payment_response["response"]
        status_pagamento = payment.get("status")  # pending, approved, rejected, cancelled, refunded, in_process, in_mediation
        preferencia_id = payment.get("preference_id")
        metodo_pagamento = payment.get("payment_method", {}).get("type", "desconhecido")
        
        logger.info(f"Pagamento {mercado_pago_id}: Status {status_pagamento}, Preferência {preferencia_id}")
        
        # Atualizar status do pagamento no banco
        resultado_update = atualizar_pagamento_status(
            preferencia_id,
            mercado_pago_id,
            status_pagamento,
            metodo_pagamento
        )
        
        presente_id = resultado_update.get("presente_id")
        
        # Se pagamento foi aprovado, marcar presente como indisponível
        if status_pagamento == "approved" and presente_id:
            sucesso = atualizar_status_presente(presente_id, "indisponivel")
            
            if sucesso:
                logger.info(f"Presente {presente_id} marcado como indisponível (pagamento aprovado)")
                registrar_webhook_log(
                    mercado_pago_id,
                    tipo_notificacao,
                    "processado",
                    data.to_dict() if hasattr(data, 'to_dict') else dict(data)
                )
            else:
                logger.error(f"Erro ao atualizar presente {presente_id} para indisponível")
                registrar_webhook_log(
                    mercado_pago_id,
                    tipo_notificacao,
                    "erro_update_presente",
                    data.to_dict() if hasattr(data, 'to_dict') else dict(data),
                    f"Erro ao atualizar presente {presente_id}"
                )
        
        elif status_pagamento in ["cancelled", "refunded"] and presente_id:
            # Se pagamento foi cancelado/reembolsado, marcar presente como disponível novamente
            sucesso = atualizar_status_presente(presente_id, "disponivel")
            
            if sucesso:
                logger.info(f"Presente {presente_id} marcado como disponível (pagamento cancelado)")
            else:
                logger.error(f"Erro ao atualizar presente {presente_id} para disponível")
        
        return jsonify({"recebido": True}), 200
        
    except Exception as e:
        logger.error(f"Erro ao processar webhook: {e}", exc_info=True)
        return jsonify({
            "recebido": False,
            "erro": str(e)
        }), 500


@pagamentos_bp.route("/sucesso_pagamento", methods=["GET"])
def sucesso_pagamento():
    """
    Página de redirecionamento após pagamento bem-sucedido.
    (Opcional - Mercado Pago redireciona aqui)
    """
    return jsonify({
        "mensagem": "Pagamento realizado com sucesso!",
        "status": "sucesso"
    }), 200


@pagamentos_bp.route("/falha_pagamento", methods=["GET"])
def falha_pagamento():
    """
    Página de redirecionamento após falha no pagamento.
    (Opcional - Mercado Pago redireciona aqui)
    """
    return jsonify({
        "mensagem": "Pagamento foi recusado",
        "status": "falha"
    }), 200


@pagamentos_bp.route("/pagamento_pendente", methods=["GET"])
def pagamento_pendente():
    """
    Página de redirecionamento para pagamento pendente.
    (Opcional - Mercado Pago redireciona aqui)
    """
    return jsonify({
        "mensagem": "Pagamento aguardando processamento",
        "status": "pendente"
    }), 200


@pagamentos_bp.route("/api/status_pagamento/<int:presente_id>", methods=["GET"])
def status_pagamento_endpoint(presente_id):
    """
    Retorna o status de pagamento de um presente (para verificação no frontend).
    """
    conn = None
    cur = None
    
    try:
        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("""
            SELECT status FROM presentes WHERE id = %s
        """, (presente_id,))
        
        resultado = cur.fetchone()
        
        if not resultado:
            return jsonify({"erro": "Presente não encontrado"}), 404
        
        return jsonify({
            "presente_id": presente_id,
            "status": resultado["status"]
        }), 200
        
    except psycopg2.Error as e:
        logger.error(f"Erro ao consultar status do presente {presente_id}: {e}")
        return jsonify({"erro": "Erro ao consultar status"}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()
