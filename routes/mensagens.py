from flask import Blueprint, render_template, request, jsonify

mensagens_bp = Blueprint("mensagens", __name__, url_prefix="/mensagens")


@mensagens_bp.route("/", methods=["GET", "POST"])
def listar():
    """
    Lista todas as mensagens deixadas pelos convidados.
    """
    if request.method == "POST":
        data = request.get_json()
        # TODO: Salvar mensagem no banco de dados usando db.insert_rsvp()
        return jsonify({"sucesso": True}), 201
    
    # TODO: Buscar mensagens do banco
    return render_template("partials/mensagens.html")


@mensagens_bp.route("/api", methods=["GET"])
def api():
    """
    API para buscar mensagens via AJAX.
    """
    # TODO: Retornar mensagens como JSON
    return jsonify([])
