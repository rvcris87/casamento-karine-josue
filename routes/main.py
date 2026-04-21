from flask import Blueprint, render_template
from db import get_presentes
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

    return render_template(
        "index.html",
        presentes=presentes
    )