from flask import Blueprint, render_template
from db import get_presentes, get_site_config, get_fotos_aprovadas

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    """
    Renderiza a página inicial com presentes, configurações e fotos aprovadas do banco de dados.
    """
    presentes = get_presentes()
    config = get_site_config()
    fotos_aprovadas = get_fotos_aprovadas()
    
    # Debug
    print(f"\n🔍 DEBUG INDEX:")
    print(f"  Presentes: {len(presentes)} encontrados")
    print(f"  Config: {config}")
    print(f"  Fotos: {len(fotos_aprovadas)} aprovadas\n")
    
    return render_template(
        "index.html",
        presentes=presentes,
        config=config,
        fotos_aprovadas=fotos_aprovadas
    )