import logging
from datetime import datetime

from flask import Blueprint, render_template

from db import get_presentes, get_site_config

logger = logging.getLogger(__name__)

main_bp = Blueprint("main", __name__)


def _formatar_data_casamento(data_casamento):
    if not data_casamento:
        return None

    if hasattr(data_casamento, "strftime"):
        return data_casamento.strftime("%d-%m-%Y")

    if isinstance(data_casamento, str):
        data_texto = data_casamento.strip()

        for formato in ("%Y-%m-%d", "%d-%m-%Y"):
            try:
                return datetime.strptime(data_texto[:10], formato).strftime("%d-%m-%Y")
            except ValueError:
                continue

        return data_texto

    return str(data_casamento)


@main_bp.route("/")
def index():
    try:
        presentes = get_presentes()
    except Exception:
        logger.exception("Erro ao carregar presentes do banco de dados.")
        presentes = []

    try:
        evento = get_site_config()
        if evento:
            evento["data_casamento_formatada"] = _formatar_data_casamento(
                evento.get("data_casamento")
            )
    except Exception:
        logger.exception("Erro ao carregar configuracoes do evento.")
        evento = None

    return render_template(
        "index.html",
        presentes=presentes,
        evento=evento
    )
