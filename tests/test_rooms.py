
from extensions import db
from models import (
    Categoria,
    ParejaCarta,
    Sala,
    SalaJugador,
    Usuario
)
from main import socketio
from room_events import emitir_actualizacion_sala

def preparar_escenario():
    """
    Crea una categoria, una sala y tres usuarios
    para realizar pruebas de gestion de salas.
    """

    categoria = Categoria(nombre="Categoria de prueba")
    db.session.add(categoria)
    db.session.flush()

    usuarios = []

    for numero in range(1, 4):
        usuario = Usuario(
            username=f"jugador{numero}",
            email=f"jugador{numero}@test.com",
            password_hash="hash_prueba"
        )

        db.session.add(usuario)
        usuarios.append(usuario)

    db.session.flush()

    sala = Sala(
        nombre="Sala de prueba",
        anfitrion_id=None,
        categoria_id=categoria.id,
        dificultad="facil",
        estado="disponible"
    )

    db.session.add(sala)
    db.session.commit()

    return sala.id, [usuario.id for usuario in usuarios]


def crear_categoria_con_parejas(nombre, cantidad):
    """
    Crea una categoria con una cantidad especifica de parejas
    para probar la seleccion de dificultades.
    """

    categoria = Categoria(nombre=nombre)

    db.session.add(categoria)
    db.session.flush()

    for numero in range(1, cantidad + 1):

        pareja = ParejaCarta(
            categoria_id=categoria.id,
            nombre=f"Par {numero}",
            imagen=f"images/pruebas/par_{numero}.png"
        )

        db.session.add(pareja)

    db.session.commit()

    return categoria.id


def test_anfitrion_puede_actualizar_configuracion(client):

    sala_id, usuarios = preparar_escenario()

    anfitrion = usuarios[0]

    categoria_id = crear_categoria_con_parejas(
        "Frutas de prueba",
        25
    )

    autenticar(client, anfitrion)

    client.post(f"/salas/{sala_id}/entrar")

    respuesta = client.post(
        f"/salas/{sala_id}/configuracion",
        json={
            "categoria_id": categoria_id,
            "dificultad": "dificil"
        }
    )

    assert respuesta.status_code == 200

    datos = respuesta.get_json()

    assert datos["categoria_id"] == categoria_id
    assert datos["dificultad"] == "dificil"
    assert datos["cantidad_pares"] == 25

    sala = db.session.get(Sala, sala_id)

    assert sala.categoria_id == categoria_id
    assert sala.dificultad == "dificil"


def test_participante_no_puede_actualizar_configuracion(client):

    sala_id, usuarios = preparar_escenario()

    anfitrion = usuarios[0]
    participante = usuarios[1]

    categoria_id = crear_categoria_con_parejas(
        "Vocaloid de prueba",
        25
    )

    autenticar(client, anfitrion)
    client.post(f"/salas/{sala_id}/entrar")

    autenticar(client, participante)
    client.post(f"/salas/{sala_id}/entrar")

    respuesta = client.post(
        f"/salas/{sala_id}/configuracion",
        json={
            "categoria_id": categoria_id,
            "dificultad": "dificil"
        }
    )

    assert respuesta.status_code == 403

    sala = db.session.get(Sala, sala_id)

    assert sala.categoria_id != categoria_id


def test_no_permite_dificultad_no_disponible(client):

    sala_id, usuarios = preparar_escenario()

    anfitrion = usuarios[0]

    categoria_id = crear_categoria_con_parejas(
        "Paw Patrol de prueba",
        9
    )

    autenticar(client, anfitrion)

    client.post(f"/salas/{sala_id}/entrar")

    respuesta = client.post(
        f"/salas/{sala_id}/configuracion",
        json={
            "categoria_id": categoria_id,
            "dificultad": "dificil"
        }
    )

    assert respuesta.status_code == 400

    sala = db.session.get(Sala, sala_id)

    assert sala.categoria_id != categoria_id


def test_cambiar_configuracion_reinicia_estado_listo(client):

    sala_id, usuarios = preparar_escenario()

    anfitrion = usuarios[0]
    participante = usuarios[1]

    categoria_id = crear_categoria_con_parejas(
        "Dragon Ball de prueba",
        25
    )

    # Ambos jugadores entran.
    autenticar(client, anfitrion)
    client.post(f"/salas/{sala_id}/entrar")

    autenticar(client, participante)
    client.post(f"/salas/{sala_id}/entrar")

    # Ambos jugadores se marcan como listos.
    autenticar(client, anfitrion)

    client.post(
        f"/salas/{sala_id}/listo",
        json={"listo": True}
    )

    autenticar(client, participante)

    client.post(
        f"/salas/{sala_id}/listo",
        json={"listo": True}
    )

    # El anfitrion cambia la configuracion.
    autenticar(client, anfitrion)

    respuesta = client.post(
        f"/salas/{sala_id}/configuracion",
        json={
            "categoria_id": categoria_id,
            "dificultad": "media"
        }
    )

    assert respuesta.status_code == 200

    # Comprobar que ambos jugadores vuelven a no estar listos.
    participaciones = SalaJugador.query.filter_by(
        sala_id=sala_id
    ).all()

    assert len(participaciones) == 2
    assert all(
        not jugador.listo
        for jugador in participaciones
    )


def autenticar(client, usuario_id):
    """
    Simula una sesion de usuario autenticado.
    """

    with client.session_transaction() as sesion:
        sesion["usuario_id"] = usuario_id


# -------------------------------------------------------------------
# Prueba 1: Listado de salas
# -------------------------------------------------------------------

def test_listar_salas_muestra_informacion_y_jugadores(client):

    categoria = Categoria(nombre="Categoria de prueba")
    db.session.add(categoria)
    db.session.flush()

    anfitrion = Usuario(
        username="jugador1",
        email="jugador1@test.com",
        password_hash="hash_prueba"
    )
    db.session.add(anfitrion)
    db.session.flush()

    sala = Sala(
        nombre="Sala de prueba",
        anfitrion_id=anfitrion.id,
        categoria_id=categoria.id,
        dificultad="facil",
        estado="esperando"
    )

    db.session.add(sala)
    db.session.flush()

    jugador = SalaJugador(
        sala_id=sala.id,
        usuario_id=anfitrion.id
    )

    db.session.add(jugador)
    db.session.commit()

    response = client.get("/salas")

    assert response.status_code == 200
    assert b"Sala de prueba" in response.data
    assert b"Categoria de prueba" in response.data
    assert b"Esperando" in response.data
    assert b"jugador1" in response.data
    assert b"1/2" in response.data


# -------------------------------------------------------------------
# Prueba 2: Entrada de dos jugadores y rechazo del tercero
# -------------------------------------------------------------------

def test_entrada_dos_jugadores_y_rechazo_de_tercero(client):

    sala_id, usuarios = preparar_escenario()

    primer_jugador = usuarios[0]
    segundo_jugador = usuarios[1]
    tercer_jugador = usuarios[2]

    # Entra el primer jugador.
    autenticar(client, primer_jugador)

    respuesta1 = client.post(
        f"/salas/{sala_id}/entrar"
    )

    assert respuesta1.status_code == 201
    assert respuesta1.get_json()["anfitrion_id"] == primer_jugador
    assert respuesta1.get_json()["jugadores"] == 1

    # Entra el segundo jugador.
    autenticar(client, segundo_jugador)

    respuesta2 = client.post(
        f"/salas/{sala_id}/entrar"
    )

    assert respuesta2.status_code == 201
    assert respuesta2.get_json()["anfitrion_id"] == primer_jugador
    assert respuesta2.get_json()["jugadores"] == 2

    # El tercer jugador intenta entrar.
    autenticar(client, tercer_jugador)

    respuesta3 = client.post(
        f"/salas/{sala_id}/entrar"
    )

    assert respuesta3.status_code == 409

    # Comprobar el estado final de la sala.
    sala = db.session.get(Sala, sala_id)

    assert sala.anfitrion_id == primer_jugador
    assert sala.estado == "esperando"

    assert SalaJugador.query.filter_by(
        sala_id=sala_id
    ).count() == 2


# -------------------------------------------------------------------
# Prueba 3: Transferencia voluntaria del anfitrion
# -------------------------------------------------------------------

def test_anfitrion_puede_transferir_su_rol(client):

    sala_id, usuarios = preparar_escenario()

    primer_jugador = usuarios[0]
    segundo_jugador = usuarios[1]

    # Entran ambos jugadores.
    autenticar(client, primer_jugador)
    client.post(f"/salas/{sala_id}/entrar")

    autenticar(client, segundo_jugador)
    client.post(f"/salas/{sala_id}/entrar")

    # El anfitrion transfiere su rol.
    autenticar(client, primer_jugador)

    respuesta = client.post(
        f"/salas/{sala_id}/transferir-anfitrion",
        json={
            "nuevo_anfitrion_id": segundo_jugador
        }
    )

    assert respuesta.status_code == 200
    assert respuesta.get_json()["anfitrion_id"] == segundo_jugador

    sala = db.session.get(Sala, sala_id)

    assert sala.anfitrion_id == segundo_jugador


# -------------------------------------------------------------------
# Prueba 4: Un participante no puede transferir el anfitrion
# -------------------------------------------------------------------

def test_participante_no_puede_transferir_el_anfitrion(client):

    sala_id, usuarios = preparar_escenario()

    primer_jugador = usuarios[0]
    segundo_jugador = usuarios[1]

    autenticar(client, primer_jugador)
    client.post(f"/salas/{sala_id}/entrar")

    autenticar(client, segundo_jugador)
    client.post(f"/salas/{sala_id}/entrar")

    # El segundo jugador intenta transferir el rol.
    respuesta = client.post(
        f"/salas/{sala_id}/transferir-anfitrion",
        json={
            "nuevo_anfitrion_id": primer_jugador
        }
    )

    assert respuesta.status_code == 403

    sala = db.session.get(Sala, sala_id)

    assert sala.anfitrion_id == primer_jugador


# -------------------------------------------------------------------
# Prueba 5: Salida del anfitrion y transferencia automatica
# -------------------------------------------------------------------

def test_salida_del_anfitrion_transfiere_el_rol(client):

    sala_id, usuarios = preparar_escenario()

    primer_jugador = usuarios[0]
    segundo_jugador = usuarios[1]

    # Entran ambos jugadores.
    autenticar(client, primer_jugador)
    client.post(f"/salas/{sala_id}/entrar")

    autenticar(client, segundo_jugador)
    client.post(f"/salas/{sala_id}/entrar")

    # El anfitrion abandona la sala.
    autenticar(client, primer_jugador)

    respuesta = client.post(
        f"/salas/{sala_id}/salir"
    )

    assert respuesta.status_code == 200
    assert respuesta.get_json()["anfitrion_id"] == segundo_jugador
    assert respuesta.get_json()["jugadores"] == 1
    assert respuesta.get_json()["estado"] == "esperando"

    sala = db.session.get(Sala, sala_id)

    assert sala.anfitrion_id == segundo_jugador
    assert sala.estado == "esperando"

    assert SalaJugador.query.filter_by(
        sala_id=sala_id
    ).count() == 1


# -------------------------------------------------------------------
# Prueba 6: Salida del ultimo jugador
# -------------------------------------------------------------------

def test_salida_del_ultimo_jugador_libera_la_sala(client):

    sala_id, usuarios = preparar_escenario()

    primer_jugador = usuarios[0]

    autenticar(client, primer_jugador)

    client.post(f"/salas/{sala_id}/entrar")

    respuesta = client.post(
        f"/salas/{sala_id}/salir"
    )

    assert respuesta.status_code == 200
    assert respuesta.get_json()["anfitrion_id"] is None
    assert respuesta.get_json()["jugadores"] == 0
    assert respuesta.get_json()["estado"] == "disponible"

    sala = db.session.get(Sala, sala_id)

    assert sala.anfitrion_id is None
    assert sala.estado == "disponible"

    assert SalaJugador.query.filter_by(
        sala_id=sala_id
    ).count() == 0


# -------------------------------------------------------------------
# Prueba 7: Un jugador puede consultar su sala
# -------------------------------------------------------------------

def test_jugador_puede_ver_su_sala(client):

    sala_id, usuarios = preparar_escenario()

    primer_jugador = usuarios[0]

    # Autenticar al jugador.
    autenticar(client, primer_jugador)

    # Entrar a la sala.
    entrada = client.post(
        f"/salas/{sala_id}/entrar"
    )

    assert entrada.status_code == 201

    # Consultar la pantalla de espera.
    respuesta = client.get(
        f"/salas/{sala_id}"
    )

    assert respuesta.status_code == 200
    assert b"jugador1" in respuesta.data
    assert b"Anfitrion" in respuesta.data
    assert b"Participantes" in respuesta.data


# -------------------------------------------------------------------
# Prueba 8: Un usuario ajeno no puede consultar la sala
# -------------------------------------------------------------------

def test_usuario_ajeno_no_puede_ver_sala(client):

    sala_id, usuarios = preparar_escenario()

    usuario_ajeno = usuarios[0]

    # El usuario tiene sesion, pero no pertenece a la sala.
    autenticar(client, usuario_ajeno)

    respuesta = client.get(
        f"/salas/{sala_id}"
    )

    assert respuesta.status_code == 302
    assert respuesta.headers["Location"].endswith("/salas")


# -------------------------------------------------------------------
# Prueba 9: Ambos jugadores pueden marcarse como listos
# -------------------------------------------------------------------

def test_dos_jugadores_pueden_marcarse_listos(client):

    sala_id, usuarios = preparar_escenario()

    primer_jugador = usuarios[0]
    segundo_jugador = usuarios[1]

    # Ambos jugadores entran a la sala.
    autenticar(client, primer_jugador)
    entrada1 = client.post(f"/salas/{sala_id}/entrar")
    assert entrada1.status_code == 201

    autenticar(client, segundo_jugador)
    entrada2 = client.post(f"/salas/{sala_id}/entrar")
    assert entrada2.status_code == 201

    # El primer jugador se marca como listo.
    autenticar(client, primer_jugador)

    respuesta1 = client.post(
        f"/salas/{sala_id}/listo",
        json={"listo": True}
    )

    assert respuesta1.status_code == 200
    assert respuesta1.get_json()["listo"] is True
    assert respuesta1.get_json()["todos_listos"] is False

    # El segundo jugador se marca como listo.
    autenticar(client, segundo_jugador)

    respuesta2 = client.post(
        f"/salas/{sala_id}/listo",
        json={"listo": True}
    )

    assert respuesta2.status_code == 200
    assert respuesta2.get_json()["todos_listos"] is True

    # Comprobar los estados individuales en la base de datos.
    participaciones = SalaJugador.query.filter_by(
        sala_id=sala_id
    ).all()

    assert len(participaciones) == 2
    assert all(jugador.listo for jugador in participaciones)

    # Persona 5 sera responsable de iniciar la partida.
    sala = db.session.get(Sala, sala_id)

    assert sala.estado == "esperando"


# -------------------------------------------------------------------
# Prueba 10: Un jugador puede cancelar su preparacion
# -------------------------------------------------------------------

def test_jugador_puede_cancelar_su_estado_listo(client):

    sala_id, usuarios = preparar_escenario()

    primer_jugador = usuarios[0]
    segundo_jugador = usuarios[1]

    # Ambos jugadores entran.
    autenticar(client, primer_jugador)
    client.post(f"/salas/{sala_id}/entrar")

    autenticar(client, segundo_jugador)
    client.post(f"/salas/{sala_id}/entrar")

    # El primer jugador se marca como listo.
    autenticar(client, primer_jugador)

    client.post(
        f"/salas/{sala_id}/listo",
        json={"listo": True}
    )

    # El mismo jugador cancela su preparacion.
    respuesta = client.post(
        f"/salas/{sala_id}/listo",
        json={"listo": False}
    )

    assert respuesta.status_code == 200
    assert respuesta.get_json()["listo"] is False
    assert respuesta.get_json()["todos_listos"] is False

    participacion = SalaJugador.query.filter_by(
        sala_id=sala_id,
        usuario_id=primer_jugador
    ).first()

    assert participacion.listo is False


# -------------------------------------------------------------------
# Prueba 11: No se puede marcar listo con un solo jugador
# -------------------------------------------------------------------

def test_no_se_puede_marcar_listo_con_un_solo_jugador(client):

    sala_id, usuarios = preparar_escenario()

    primer_jugador = usuarios[0]

    autenticar(client, primer_jugador)

    entrada = client.post(
        f"/salas/{sala_id}/entrar"
    )

    assert entrada.status_code == 201

    respuesta = client.post(
        f"/salas/{sala_id}/listo",
        json={"listo": True}
    )

    assert respuesta.status_code == 409

    participacion = SalaJugador.query.filter_by(
        sala_id=sala_id,
        usuario_id=primer_jugador
    ).first()

    assert participacion.listo is False


# -------------------------------------------------------------------
# Prueba 12: Un usuario ajeno no puede cambiar el estado
# -------------------------------------------------------------------

def test_usuario_ajeno_no_puede_modificar_estado_listo(client):

    sala_id, usuarios = preparar_escenario()

    primer_jugador = usuarios[0]
    segundo_jugador = usuarios[1]
    usuario_ajeno = usuarios[2]

    # Los dos participantes ingresan.
    autenticar(client, primer_jugador)
    client.post(f"/salas/{sala_id}/entrar")

    autenticar(client, segundo_jugador)
    client.post(f"/salas/{sala_id}/entrar")

    # Un tercer usuario intenta modificar la preparacion.
    autenticar(client, usuario_ajeno)

    respuesta = client.post(
        f"/salas/{sala_id}/listo",
        json={"listo": True}
    )

    assert respuesta.status_code == 403

    # Comprobar que los estados no fueron modificados.
    participaciones = SalaJugador.query.filter_by(
        sala_id=sala_id
    ).all()

    assert len(participaciones) == 2
    assert all(
        not jugador.listo
        for jugador in participaciones
    )


# -------------------------------------------------------------------
# Prueba 17: Un participante puede unirse al canal de Socket.IO
# -------------------------------------------------------------------

def test_socketio_participante_puede_unirse_a_su_sala(client, app):

    sala_id, usuarios = preparar_escenario()

    jugador = usuarios[0]

    # Autenticar al jugador.
    autenticar(client, jugador)

    # Registrar al jugador en la sala.
    respuesta = client.post(
        f"/salas/{sala_id}/entrar"
    )

    assert respuesta.status_code == 201

    # Crear conexion Socket.IO usando la sesion del cliente Flask.
    socket_client = socketio.test_client(
        app,
        flask_test_client=client
    )

    assert socket_client.is_connected()

    # Solicitar acceso al canal de la sala.
    socket_client.emit(
        "unirse_sala",
        {"sala_id": sala_id}
    )

    eventos = socket_client.get_received()

    assert any(
        evento["name"] == "sala_unida"
        and evento["args"][0]["ok"] is True
        for evento in eventos
    )

    socket_client.disconnect()

# -------------------------------------------------------------------
# Prueba 18: Un usuario ajeno no puede entrar al canal
# -------------------------------------------------------------------

def test_socketio_usuario_ajeno_no_puede_unirse(client, app):

    sala_id, usuarios = preparar_escenario()

    usuario_ajeno = usuarios[0]

    # El usuario tiene una sesion, pero no esta registrado en la sala.
    autenticar(client, usuario_ajeno)

    socket_client = socketio.test_client(
        app,
        flask_test_client=client
    )

    socket_client.emit(
        "unirse_sala",
        {"sala_id": sala_id}
    )

    eventos = socket_client.get_received()

    assert any(
        evento["name"] == "error_sala"
        for evento in eventos
    )

    socket_client.disconnect()

# -------------------------------------------------------------------
# Prueba 19: Un usuario sin sesion no puede entrar al canal
# -------------------------------------------------------------------

def test_socketio_usuario_sin_sesion_no_puede_unirse(client, app):

    # Crear una sala de prueba.
    sala_id, _ = preparar_escenario()

    # No se establece session["usuario_id"].
    socket_client = socketio.test_client(
        app,
        flask_test_client=client
    )

    socket_client.emit(
        "unirse_sala",
        {"sala_id": sala_id}
    )

    eventos = socket_client.get_received()

    assert any(
        evento["name"] == "error_sala"
        for evento in eventos
    )

    socket_client.disconnect()

# -------------------------------------------------------------------
# Prueba 20: Los eventos se limitan al canal correspondiente
# -------------------------------------------------------------------

def test_socketio_no_envia_eventos_a_otra_sala(client, app):

    sala_id, usuarios = preparar_escenario()

    # Crear una segunda sala usando la misma categoria.
    sala_original = db.session.get(Sala, sala_id)

    # Registrar al primer usuario en la primera sala.
    sala_original.anfitrion_id = usuarios[0]

    db.session.add(
        SalaJugador(
            sala_id=sala_id,
            usuario_id=usuarios[0],
            listo=False
        )
    )

    segunda_sala = Sala(
        nombre="Sala secundaria",
        anfitrion_id=usuarios[2],
        categoria_id=sala_original.categoria_id,
        dificultad="facil",
        estado="esperando"
    )

    db.session.add(segunda_sala)
    db.session.flush()

    db.session.add(
        SalaJugador(
            sala_id=segunda_sala.id,
            usuario_id=usuarios[2],
            listo=False
        )
    )

    db.session.commit()

    # Crear dos clientes Flask independientes.
    cliente1 = app.test_client()
    cliente2 = app.test_client()

    # Cada usuario pertenece a una sala diferente.
    autenticar(cliente1, usuarios[0])
    autenticar(cliente2, usuarios[2])

    # Crear conexiones Socket.IO.
    socket1 = socketio.test_client(
        app,
        flask_test_client=cliente1
    )

    socket2 = socketio.test_client(
        app,
        flask_test_client=cliente2
    )

    # Cada cliente se incorpora a su propio canal.
    socket1.emit(
        "unirse_sala",
        {"sala_id": sala_id}
    )

    socket2.emit(
        "unirse_sala",
        {"sala_id": segunda_sala.id}
    )

    # Limpiar las respuestas de confirmacion inicial.
    socket1.get_received()
    socket2.get_received()

    # Emitir una actualizacion exclusivamente a la primera sala.
    with app.app_context():
        emitir_actualizacion_sala(sala_id)

    eventos_sala1 = socket1.get_received()
    eventos_sala2 = socket2.get_received()

    assert any(
        evento["name"] == "sala_actualizada"
        for evento in eventos_sala1
    )

    assert not any(
        evento["name"] == "sala_actualizada"
        for evento in eventos_sala2
    )

    socket1.disconnect()
    socket2.disconnect()



