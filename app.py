import os
import logging
from flask import Flask
from dotenv import load_dotenv

load_dotenv()

# Logging profissional
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

from db import formatar_valor_brl

from routes.main import main_bp
from routes.fotos import fotos_bp
from routes.admin import admin_bp
from routes.rsvp import rsvp_bp
from routes.pagamentos import pagamentos_bp

# Validacao de variaveis de ambiente criticas
DATABASE_URL = os.getenv("DATABASE_URL")
SECRET_KEY = os.getenv("SECRET_KEY")
PAGBANK_TOKEN = os.getenv("PAGBANK_TOKEN")
PAGBANK_ENV = os.getenv("PAGBANK_ENV", "production")
PAGBANK_API_URL = os.getenv("PAGBANK_API_URL", "https://api.pagseguro.com")


# Validar DATABASE_URL (critico - aplicacao nao funciona sem)
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL nao configurada no .env - aplicacao nao pode iniciar")

# Validar PagBank (critico - pagamentos nao funcionam sem)
logger.info("PagBank token configurado: %s", "sim" if PAGBANK_TOKEN else "nao")
logger.info("PagBank ambiente: %s, API URL: %s", PAGBANK_ENV, PAGBANK_API_URL)

if not PAGBANK_TOKEN:
    raise RuntimeError("PAGBANK_TOKEN nao configurado no .env - pagamentos desativados")

# Validar SECRET_KEY (critico - sessoes nao funcionam sem)
if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY nao configurada no .env - sessoes nao funcionarao sem ela")

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")
app.jinja_env.filters["brl"] = formatar_valor_brl

app.register_blueprint(main_bp)
app.register_blueprint(fotos_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(rsvp_bp)
app.register_blueprint(pagamentos_bp)

logger.info("Aplicacao Flask inicializada com sucesso.")

if __name__ == "__main__":
    app.run(debug=False)
