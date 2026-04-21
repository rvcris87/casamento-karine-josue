from flask import Blueprint, render_template
from db import get_presentes

main_bp = Blueprint("main", __name__)

@main_bp.route("/")
def index():
    presentes = get_presentes()

    return render_template(
        "index.html",
        presentes=presentes
    )