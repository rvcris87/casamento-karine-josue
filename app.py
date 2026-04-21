import os
import logging
from flask import Flask
from dotenv import load_dotenv
from db import formatar_valor_brl

from routes.main import main_bp
from routes.fotos import fotos_bp
from routes.admin import admin_bp
from routes.rsvp import rsvp_bp
from routes.pagamentos import pagamentos_bp

load_dotenv()

# Logging profissional
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

# Validação de variáveis de ambiente críticas
DATABASE_URL = os.getenv("DATABASE_URL")
SECRET_KEY = os.getenv("SECRET_KEY", "chave-padrao-insegura")

if not DATABASE_URL:
    logger.error("ERRO CRÍTICO: DATABASE_URL não configurada. O banco de dados não funcionará.")

if SECRET_KEY == "chave-padrao-insegura":
    logger.warning("SECRET_KEY não configurada. Use uma chave segura em produção.")

app = Flask(__name__)
app.config["SECRET_KEY"] = SECRET_KEY
app.jinja_env.filters["brl"] = formatar_valor_brl

app.register_blueprint(main_bp)
app.register_blueprint(fotos_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(rsvp_bp)
app.register_blueprint(pagamentos_bp)

logger.info("Aplicação Flask inicializada com sucesso.")

if __name__ == "__main__":
    app.run(debug=False)