import logging
import os
from datetime import datetime

from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for
from werkzeug.utils import secure_filename

from db import get_fotos_aprovadas, salvar_foto_convidado

fotos_bp = Blueprint("fotos", __name__, url_prefix="/fotos")
logger = logging.getLogger(__name__)

UPLOAD_FOLDER = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "static",
    "uploads",
    "convidados",
)
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}
MAX_FILE_SIZE = 5 * 1024 * 1024

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def arquivo_permitido(filename):
    """Verifica se o arquivo tem extensao permitida."""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def validar_arquivo(file):
    """Valida o arquivo de upload."""
    if not file or file.filename == "":
        return False, "Nenhum arquivo selecionado"

    if not arquivo_permitido(file.filename):
        return False, "Formato nao permitido. Use jpg, jpeg, png ou webp"

    file.seek(0, os.SEEK_END)
    tamanho = file.tell()
    file.seek(0)

    if tamanho > MAX_FILE_SIZE:
        tamanho_mb = tamanho / (1024 * 1024)
        return False, f"Arquivo muito grande. Maximo permitido: 5MB (seu arquivo: {tamanho_mb:.1f}MB)"

    if tamanho == 0:
        return False, "Arquivo vazio"

    return True, None


@fotos_bp.route("/galeria")
def galeria():
    fotos = get_fotos_aprovadas()
    return render_template("partials/galeria.html", fotos=fotos)


@fotos_bp.route("/enviar", methods=["GET", "POST"])
def enviar_foto():
    if request.method == "POST":
        nome_convidado = request.form.get("nome", "").strip()
        legenda = request.form.get("legenda", "").strip()

        if not nome_convidado or len(nome_convidado) < 3:
            flash("❌ Por favor, forneça seu nome (mínimo 3 caracteres)", "error")
            return redirect(url_for("fotos.enviar_foto"))

        files = request.files.getlist("fotos")
        if not files or all(f.filename == "" for f in files):
            flash("❌ Nenhum arquivo selecionado", "error")
            return redirect(url_for("fotos.enviar_foto"))

        sucesso_count = 0
        erro_count = 0

        for file in files:
            if file.filename == "":
                continue

            valido, mensagem_erro = validar_arquivo(file)
            if not valido:
                flash(f"❌ {file.filename}: {mensagem_erro}", "error")
                erro_count += 1
                continue

            try:
                filename = secure_filename(file.filename)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_")
                filename_unico = timestamp + filename
                filepath = os.path.join(UPLOAD_FOLDER, filename_unico)

                file.save(filepath)

                imagem_url = f"/static/uploads/convidados/{filename_unico}"
                salvar_foto_convidado(nome_convidado, legenda, imagem_url)

                sucesso_count += 1
                logger.info("Foto enviada por %s: %s", nome_convidado, filename_unico)
            except Exception as e:
                logger.exception("Erro ao processar arquivo %s: %s", file.filename, e)
                flash(f"Erro ao salvar {file.filename} no banco de dados", "erro")
                erro_count += 1

        if sucesso_count > 0:
            flash("Fotos enviadas com sucesso! Elas serão publicadas após aprovação.", "sucesso")
        if erro_count > 0:
            flash(f"⚠️  {erro_count} arquivo(s) não pode(m) ser enviado(s)", "warning")

        return redirect(url_for("main.index") + "#fotos-convidados")

    return render_template("partials/fotos_convidados.html")


@fotos_bp.route("/api/aprovadas")
def api_fotos_aprovadas():
    fotos = get_fotos_aprovadas()
    return jsonify([dict(foto) for foto in fotos])
