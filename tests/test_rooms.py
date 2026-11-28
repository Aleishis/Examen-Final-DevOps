
from extensions import db
from models import Categoria, Sala, SalaJugador, Usuario


def test_listar_salas_muestra_informacion_y_jugadores(client):
    # Crear una categoría.
    categoria = Categoria(nombre="Categoria de prueba")
    db.session.add(categoria)
    db.session.flush()

    # Crear un usuario que será anfitrión.
    anfitrion = Usuario(
        username="jugador1",
        email="jugador1@test.com",
        password_hash="hash_prueba"
    )
    db.session.add(anfitrion)
    db.session.flush()

    # Crear una sala en estado esperando.
    sala = Sala(
        nombre="Sala de prueba",
        anfitrion_id=anfitrion.id,
        categoria_id=categoria.id,
        dificultad="facil",
        estado="esperando"
    )
    db.session.add(sala)
    db.session.flush()

    # Registrar al primer jugador.
    jugador = SalaJugador(
        sala_id=sala.id,
        usuario_id=anfitrion.id
    )
    db.session.add(jugador)

    db.session.commit()

    # Consultar el listado.
    response = client.get("/salas")

    assert response.status_code == 200
    assert b"Sala de prueba" in response.data
    assert b"Categoria de prueba" in response.data
    assert b"Esperando" in response.data
    assert b"jugador1" in response.data
    assert b"1/2" in response.data
