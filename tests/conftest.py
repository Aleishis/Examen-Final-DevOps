import os

# Las pruebas usan SQLite en memoria: no necesitan MySQL ni Docker.
# Debe definirse antes de importar main, que lee la configuración al cargarse.
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["SECRET_KEY"] = "pruebas"

import pytest  # noqa: E402

from main import app as flask_app  # noqa: E402
from main import socketio  # noqa: E402
from extensions import db


@pytest.fixture
def app():
    flask_app.config.update(TESTING=True)
    with flask_app.app_context():
        db.create_all()
        yield flask_app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def socket_client(app):
    sc = socketio.test_client(app)
    yield sc
    if sc.is_connected():
        sc.disconnect()
