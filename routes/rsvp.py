from flask import Blueprint, request, redirect, url_for, flash
from db import salvar_rsvp

rsvp_bp = Blueprint("rsvp", __name__, url_prefix="/rsvp")


@rsvp_bp.route("/enviar", methods=["POST"])
def enviar_rsvp():
    nome = request.form.get("nome", "").strip()
    telefone = request.form.get("telefone", "").strip()
    acompanhantes = request.form.get("acompanhantes", "0").strip()
    quantidade_criancas = request.form.get("quantidade_criancas", "0").strip()
    confirmacao = request.form.get("confirmacao", "").strip().lower()
    observacao = request.form.get("observacao", "").strip()

    if not nome:
        flash("Informe seu nome para confirmar presença.", "erro")
        return redirect(url_for("main.index") + "#rsvp")

    if confirmacao not in ("sim", "nao"):
        flash("Selecione uma opção válida de confirmação.", "erro")
        return redirect(url_for("main.index") + "#rsvp")

    try:
        acompanhantes = int(acompanhantes) if acompanhantes else 0
        if acompanhantes < 0:
            acompanhantes = 0
    except ValueError:
        acompanhantes = 0

    try:
        quantidade_criancas = int(quantidade_criancas) if quantidade_criancas else 0
        if quantidade_criancas < 0:
            quantidade_criancas = 0
    except ValueError:
        quantidade_criancas = 0

    try:
        salvar_rsvp(nome, telefone, acompanhantes, quantidade_criancas, confirmacao, observacao)
        flash("Confirmação enviada com sucesso! 💙", "sucesso")
    except Exception as e:
        print("ERRO AO SALVAR RSVP:", repr(e))
        flash("Não foi possível enviar sua confirmação agora.", "erro")

    return redirect(url_for("main.index") + "#rsvp")
