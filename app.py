from flask import Flask
from dotenv import load_dotenv
import os

from routes.main import main_bp
from routes.fotos import fotos_bp
from routes.admin import admin_bp
from routes.rsvp import rsvp_bp

load_dotenv()

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "chave-padrao")

app.register_blueprint(main_bp)
app.register_blueprint(fotos_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(rsvp_bp)

if __name__ == "__main__":
    app.run(debug=True)