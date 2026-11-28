
from flask import current_app, session
from flask_socketio import emit, join_room
from sqlalchemy import select

from extensions import db
from models import Sala, SalaJugador, Categoria, Usuario


# -------------------------------------------------------------------
# Utilidades de comunicacion
# -------------------------------------------------------------------

def obtener_usuario_socket():
    """
    Obtiene el usuario autenticado desde la sesion Flask.

    Utiliza la misma clave que las rutas HTTP:
    session["usuario_id"].
    """
    valor = session.get("usuario_id")

    if isinstance(valor, bool):
        return None

    try:
        return int(valor) if valor is not None else None
    except (TypeError, ValueError):
        return None


def nombre_canal_sala(sala_id):
    """
    Genera el nombre del canal de comunicacion de una sala.
    """
    return f"sala_{sala_id}"


# -------------------------------------------------------------------
# Obtener el estado publico de una sala
# -------------------------------------------------------------------

def obtener_estado_publico_sala(sala_id):
    """
    Obtiene la informacion que pueden consultar los participantes
    de una sala mediante Socket.IO.
    """

    sala = db.session.get(Sala, sala_id)

    if sala is None:
        return None

    categoria = db.session.get(
        Categoria,
        sala.categoria_id
    )

    registros = (
        db.session.query(SalaJugador, Usuario)
        .join(
            Usuario,
            Usuario.id == SalaJugador.usuario_id
        )
        .filter(SalaJugador.sala_id == sala_id)
        .order_by(
            SalaJugador.fecha_union.asc(),
            SalaJugador.id.asc()
        )
        .all()
    )

    jugadores = []

    for participacion, usuario in registros:

        jugadores.append({
            "id": usuario.id,
            "username": usuario.username,
            "listo": participacion.listo,
            "anfitrion": (
                usuario.id == sala.anfitrion_id
            )
        })

    todos_listos = (
        len(jugadores) == 2
        and all(jugador["listo"] for jugador in jugadores)
    )

    return {
        "sala_id": sala.id,
        "nombre": sala.nombre,
        "estado": sala.estado,
        "categoria_id": sala.categoria_id,
        "categoria": categoria.nombre if categoria else None,
        "dificultad": sala.dificultad,
        "anfitrion_id": sala.anfitrion_id,
        "jugadores": jugadores,
        "cantidad_jugadores": len(jugadores),
        "todos_listos": todos_listos
    }


# -------------------------------------------------------------------
# Emitir actualizacion a una sala especifica
# -------------------------------------------------------------------

def emitir_actualizacion_sala(sala_id):
    """
    Envia el estado actualizado exclusivamente a los clientes
    conectados al canal de la sala indicada.
    """

    socketio = current_app.extensions.get("socketio")

    if socketio is None:
        return

    estado = obtener_estado_publico_sala(sala_id)

    if estado is None:
        return

    socketio.emit(
        "sala_actualizada",
        estado,
        to=nombre_canal_sala(sala_id)
    )


# -------------------------------------------------------------------
# Registro de eventos de Flask-SocketIO
# -------------------------------------------------------------------

def registrar_eventos_salas(socketio):

    @socketio.on("unirse_sala")
    def manejar_unirse_sala(datos):

        usuario_id = obtener_usuario_socket()

        # Comprobar que exista una sesion autenticada.
        if usuario_id is None:
            emit(
                "error_sala",
                {
                    "mensaje": "Debes iniciar sesion para conectarte a una sala."
                }
            )
            return

        # Validar los datos recibidos.
        if not isinstance(datos, dict):
            emit(
                "error_sala",
                {
                    "mensaje": "Los datos de la sala no son validos."
                }
            )
            return

        sala_id_recibido = datos.get("sala_id")

        if isinstance(sala_id_recibido, bool):
            emit(
                "error_sala",
                {
                    "mensaje": "El identificador de la sala no es valido."
                }
            )
            return

        try:
            sala_id = int(sala_id_recibido)
        except (TypeError, ValueError):
            emit(
                "error_sala",
                {
                    "mensaje": "El identificador de la sala no es valido."
                }
            )
            return

        # Comprobar que la sala exista.
        sala = db.session.get(Sala, sala_id)

        if sala is None:
            emit(
                "error_sala",
                {
                    "mensaje": "La sala solicitada no existe."
                }
            )
            return

        # Comprobar que el usuario pertenezca a la sala.
        participacion = db.session.execute(
            select(SalaJugador).where(
                SalaJugador.sala_id == sala_id,
                SalaJugador.usuario_id == usuario_id
            )
        ).scalar_one_or_none()

        if participacion is None:
            emit(
                "error_sala",
                {
                    "mensaje": "No perteneces a esta sala."
                }
            )
            return

        # Unir el socket al canal correspondiente.
        join_room(nombre_canal_sala(sala_id))

        # Enviar el estado actual solamente al usuario que se acaba
        # de incorporar al canal.
        estado = obtener_estado_publico_sala(sala_id)

        emit(
            "sala_unida",
            {
                "ok": True,
                "mensaje": "Conexion establecida con la sala.",
                "sala": estado
            }
        )
