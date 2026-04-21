from flask import Blueprint, request, jsonify
from db import get_connection

pagamentos_bp = Blueprint("pagamentos", __name__)

@pagamentos_bp.route("/api/presentear", methods=["POST"])
def criar_pagamento_presente():
    data = request.json

    presente_id = data.get("presente_id")
    nome = data.get("nome_pagador")
    email = data.get("email_pagador")
    telefone = data.get("telefone_pagador")
    mensagem = data.get("mensagem_pagador")

    conn = None
    cur = None

    try:
        conn = get_connection()
        cur = conn.cursor()

        # pega valor do presente
        cur.execute("""
            SELECT valor FROM presentes WHERE id = %s
        """, (presente_id,))
        result = cur.fetchone()

        if not result:
            return jsonify({"erro": "Presente não encontrado"}), 404

        valor = result[0]

        # cria registro de pagamento
        cur.execute("""
            INSERT INTO pagamentos_presentes
            (presente_id, nome_pagador, email_pagador, telefone_pagador, mensagem, valor)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (presente_id, nome, email, telefone, mensagem, valor))

        pagamento_id = cur.fetchone()[0]

        conn.commit()

        return jsonify({
            "sucesso": True,
            "pagamento_id": pagamento_id,
            "valor": float(valor)
        })

    except Exception as e:
        print(e)
        return jsonify({"erro": "Erro ao criar pagamento"}), 500

    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()
