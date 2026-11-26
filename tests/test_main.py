from extensions import db


def test_index_responde_200(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "Memorama PvP".encode() in response.data


def test_health_ok_con_base_de_datos(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok", "database": "ok"}


def test_health_503_si_falla_la_base_de_datos(client, monkeypatch):
    def falla(*args, **kwargs):
        raise RuntimeError("sin conexión")

    monkeypatch.setattr(db.session, "execute", falla)
    response = client.get("/health")
    assert response.status_code == 503
    assert response.get_json()["database"] == "error"


def test_ruta_inexistente_404(client):
    assert client.get("/no-existe").status_code == 404


def test_archivos_estaticos_disponibles(client):
    assert client.get("/static/css/styles.css").status_code == 200
    assert client.get("/static/js/main.js").status_code == 200


def test_socketio_conecta(socket_client):
    assert socket_client.is_connected()
