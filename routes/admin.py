import os
from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from dotenv import load_dotenv

from db import (
    get_todas_fotos,
    get_todos_presentes_admin,
    alternar_status_presente,
    alternar_destaque_foto,
    excluir_foto,
    get_todos_rsvp,
    get_rsvp_por_id,
    atualizar_rsvp,
    excluir_rsvp
)

load_dotenv()

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


def login_required_admin(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not session.get("admin_logado"):
            flash("Faça login para acessar o painel administrativo.", "erro")
            return redirect(url_for("admin.login_admin"))
        return func(*args, **kwargs)
    return wrapper


@admin_bp.route("/login", methods=["GET", "POST"])
def login_admin():
    if request.method == "POST":
        usuario = request.form.get("usuario", "").strip()
        senha = request.form.get("senha", "").strip()

        admin_user = os.getenv("ADMIN_USERNAME")
        admin_password = os.getenv("ADMIN_PASSWORD")

        if usuario == admin_user and senha == admin_password:
            session["admin_logado"] = True
            flash("Login realizado com sucesso.", "sucesso")
            return redirect(url_for("admin.admin_fotos"))

        flash("Usuário ou senha inválidos.", "erro")

    return render_template("admin_login.html")


@admin_bp.route("/logout", methods=["POST"])
def logout_admin():
    session.pop("admin_logado", None)
    flash("Você saiu do painel administrativo.", "sucesso")
    return redirect(url_for("admin.login_admin"))


@admin_bp.route("/fotos")
@login_required_admin
def admin_fotos():
    fotos = get_todas_fotos()
    return render_template("admin_fotos.html", fotos=fotos)


@admin_bp.route("/presentes")
@login_required_admin
def admin_presentes():
    presentes = get_todos_presentes_admin()
    return render_template("admin_presentes.html", presentes=presentes)


@admin_bp.route("/presentes/<int:presente_id>/status", methods=["POST"])
@login_required_admin
def alternar_presente_status(presente_id):
    novo_status = alternar_status_presente(presente_id)
    if novo_status:
        flash(f"Presente marcado como {novo_status}.", "sucesso")
    else:
        flash("Presente nao encontrado.", "erro")
    return redirect(url_for("admin.admin_presentes"))





@admin_bp.route("/fotos/<int:foto_id>/destacar", methods=["POST"])
@login_required_admin
def destacar_foto(foto_id):
    destaque = request.form.get("destaque") == "true"
    alternar_destaque_foto(foto_id, destaque)
    flash("Destaque da foto atualizado.", "sucesso")
    return redirect(url_for("admin.admin_fotos"))


@admin_bp.route("/fotos/<int:foto_id>/excluir", methods=["POST"])
@login_required_admin
def remover_foto(foto_id):
    excluir_foto(foto_id)
    flash("Foto excluída com sucesso.", "erro")
    return redirect(url_for("admin.admin_fotos"))


@admin_bp.route("/rsvp")
@login_required_admin
def admin_rsvp():
    lista_rsvp = get_todos_rsvp()
    return render_template("admin_rsvp.html", lista_rsvp=lista_rsvp)


def _parse_quantidade(valor):
    try:
        quantidade = int(valor) if valor else 0
        return max(quantidade, 0)
    except ValueError:
        return 0


@admin_bp.route("/rsvp/<int:rsvp_id>/editar", methods=["GET", "POST"])
@login_required_admin
def editar_rsvp(rsvp_id):
    rsvp = get_rsvp_por_id(rsvp_id)
    if not rsvp:
        flash("Confirmacao de presenca nao encontrada.", "erro")
        return redirect(url_for("admin.admin_rsvp"))

    if request.method == "POST":
        nome = request.form.get("nome_convidado", "").strip()
        telefone = request.form.get("telefone", "").strip()
        acompanhantes = _parse_quantidade(request.form.get("acompanhantes", "0").strip())
        quantidade_criancas = _parse_quantidade(request.form.get("quantidade_criancas", "0").strip())
        confirmacao = request.form.get("confirmacao", "").strip().lower()
        observacao = request.form.get("observacao", "").strip()

        if not nome:
            flash("Informe o nome do convidado.", "erro")
            return render_template("admin_rsvp_editar.html", rsvp=rsvp)

        if confirmacao not in ("sim", "nao"):
            flash("Selecione uma opcao valida de confirmacao.", "erro")
            return render_template("admin_rsvp_editar.html", rsvp=rsvp)

        try:
            atualizado = atualizar_rsvp(
                rsvp_id,
                nome,
                telefone,
                acompanhantes,
                quantidade_criancas,
                confirmacao,
                observacao
            )
            if atualizado:
                flash("Confirmacao de presenca atualizada com sucesso.", "sucesso")
            else:
                flash("Confirmacao de presenca nao encontrada.", "erro")
            return redirect(url_for("admin.admin_rsvp"))
        except Exception:
            flash("Nao foi possivel atualizar a confirmacao de presenca.", "erro")

    return render_template("admin_rsvp_editar.html", rsvp=rsvp)


@admin_bp.route("/rsvp/<int:rsvp_id>/excluir", methods=["POST"])
@login_required_admin
def remover_rsvp(rsvp_id):
    try:
        removido = excluir_rsvp(rsvp_id)
        if removido:
            flash("Confirmacao de presenca excluida com sucesso.", "sucesso")
        else:
            flash("Confirmacao de presenca nao encontrada.", "erro")
    except Exception:
        flash("Nao foi possivel excluir a confirmacao de presenca.", "erro")

    return redirect(url_for("admin.admin_rsvp"))
