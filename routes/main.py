from flask import Blueprint, render_template
from db import get_presentes, get_site_config
import logging

logger = logging.getLogger(__name__)

main_bp = Blueprint("main", __name__)

@main_bp.route("/")
def index():
    try:
        presentes = get_presentes()
    except Exception:
        logger.exception("Erro ao carregar presentes do banco de dados.")
        presentes = []

    try:
        evento = get_site_config()
    except Exception:
        logger.exception("Erro ao carregar configurações do evento.")
        evento = None

    return render_template(
        "index.html",
        presentes=presentes,
        evento=evento
    )