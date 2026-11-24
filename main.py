"""
Cada módulo del equipo agrega sus rutas y eventos en la sección marcada
con su nombre para reducir conflictos al hacer merge
"""
import os

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template
from flask_migrate import Migrate
from flask_socketio import SocketIO
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text

load_dotenv()

app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.getenv("SECRET_KEY", "dev-solo-local-cambiar"),
    SQLALCHEMY_DATABASE_URI=os.getenv("DATABASE_URL", "sqlite:///memorama.db"),
    SQLALCHEMY_ENGINE_OPTIONS={"pool_pre_ping": True},
    UPLOAD_FOLDER=os.getenv(
        "UPLOAD_FOLDER", os.path.join(app.root_path, "static", "uploads")
    ),
    MAX_CONTENT_LENGTH=5 * 1024 * 1024,  # 5 MB por imagen subida
)

db = SQLAlchemy(app)
migrate = Migrate(app, db)

import models  # noqa: F401

# Un solo proceso (gunicorn -w 1): las salas de Socket.IO viven en memoria.
socketio = SocketIO(app)


# --------------------------------------------------------------------------
# Rutas base / DevOps
# --------------------------------------------------------------------------
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/health")
def health():
    """Usado por Docker y por el pipeline de despliegue para validar la app."""
    try:
        db.session.execute(text("SELECT 1"))
        database = "ok"
    except Exception:
        database = "error"
    status = "ok" if database == "ok" else "degraded"
    code = 200 if status == "ok" else 503
    return jsonify(status=status, database=database), code


# --------------------------------------------------------------------------
# Persona 3: Modelos y CRUD de categorías / parejas de cartas
# --------------------------------------------------------------------------


# --------------------------------------------------------------------------
# Persona 4: Salas (lista, anfitrión, listos, eventos Socket.IO por sala)
# --------------------------------------------------------------------------


# --------------------------------------------------------------------------
# Persona 5: Lógica del juego (tablero, turnos, parejas, ganador)
# --------------------------------------------------------------------------


# --------------------------------------------------------------------------
# Persona 6: Usuarios, historial y estadísticas
# --------------------------------------------------------------------------


if __name__ == "__main__":
    socketio.run(
        app,
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
        debug=os.getenv("FLASK_DEBUG", "0") == "1",
        allow_unsafe_werkzeug=True,  # solo para desarrollo produccion usa gunicorn
    )
