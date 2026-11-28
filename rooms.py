
from flask import Blueprint, jsonify, render_template, request, session
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from extensions import db
from models import Sala, SalaJugador, Categoria, Usuario


rooms_bp = Blueprint("rooms", __name__)


# -------------------------------------------------------------------
# Utilidades para la gestion de salas
# -------------------------------------------------------------------

def obtener_usuario_sesion():
    """
    Obtiene el ID del usuario autenticado desde la sesion Flask.

    Persona 6 debera establecer session["usuario_id"]
    cuando implemente el inicio de sesion.
    """
    valor = session.get("usuario_id")

    try:
        return int(valor) if valor is not None else None
    except (TypeError, ValueError):
        return None


def respuesta_error(mensaje, codigo):
    """Devuelve una respuesta JSON de error."""
    return jsonify({
        "ok": False,
        "mensaje": mensaje
    }), codigo


def obtener_sala_bloqueada(sala_id):
    """
    Obtiene una sala bloqueando su registro durante la transaccion.

    En MySQL, FOR UPDATE ayuda a evitar que dos usuarios
    ocupen simultaneamente el ultimo espacio disponible.
    """
    consulta = (
        select(Sala)
        .where(Sala.id == sala_id)
        .with_for_update()
    )

    return db.session.execute(consulta).scalar_one_or_none()


# -------------------------------------------------------------------
# Actividad 1: Listado de salas
# -------------------------------------------------------------------

@rooms_bp.route("/salas", methods=["GET"])
def listar_salas():

    registros = (
        db.session.query(Sala, Categoria, Usuario)
        .join(Categoria, Categoria.id == Sala.categoria_id)
        .outerjoin(Usuario, Usuario.id == Sala.anfitrion_id)
        .order_by(Sala.id.asc())
        .all()
    )

    # Contar los jugadores registrados en cada sala.
    conteos = (
        db.session.query(
            SalaJugador.sala_id,
            func.count(SalaJugador.id)
        )
        .group_by(SalaJugador.sala_id)
        .all()
    )

    jugadores_por_sala = {
        sala_id: cantidad
        for sala_id, cantidad in conteos
    }

    # Convertir los estados internos en etiquetas legibles.
    etiquetas_estado = {
        "disponible": "Disponible",
        "esperando": "Esperando",
        "en_curso": "En curso"
    }

    etiquetas_dificultad = {
        "facil": "Fácil",
        "media": "Media",
        "dificil": "Difícil"
    }

    salas = []

    for sala, categoria, anfitrion in registros:

        salas.append({
            "id": sala.id,
            "nombre": sala.nombre,
            "estado": sala.estado,
            "estado_texto": etiquetas_estado.get(
                sala.estado, sala.estado
            ),
            "categoria": categoria.nombre,
            "dificultad": etiquetas_dificultad.get(
                sala.dificultad, sala.dificultad
            ),
            "anfitrion": (
                anfitrion.username if anfitrion else None
            ),
            "jugadores": jugadores_por_sala.get(sala.id, 0)
        })

    return render_template("rooms.html", salas=salas)


# -------------------------------------------------------------------
# Actividad 2: Entrada de jugadores
# -------------------------------------------------------------------

@rooms_bp.route(
    "/salas/<int:sala_id>/entrar",
    methods=["POST"]
)
def entrar_sala(sala_id):

    usuario_id = obtener_usuario_sesion()

    if usuario_id is None:
        return respuesta_error(
            "Debes iniciar sesion para entrar a una sala.",
            401
        )

    try:
        # Bloquear la sala durante la operacion.
        sala = obtener_sala_bloqueada(sala_id)

        if sala is None:
            db.session.rollback()
            return respuesta_error(
                "La sala solicitada no existe.",
                404
            )

        # Comprobar que el usuario exista.
        usuario = db.session.get(Usuario, usuario_id)

        if usuario is None:
            db.session.rollback()
            return respuesta_error(
                "El usuario de la sesion no existe.",
                401
            )

        # Comprobar si el usuario ya pertenece a esta sala.
        participacion = db.session.execute(
            select(SalaJugador).where(
                SalaJugador.sala_id == sala_id,
                SalaJugador.usuario_id == usuario_id
            )
        ).scalar_one_or_none()

        if participacion is not None:
            cantidad = db.session.scalar(
                select(func.count(SalaJugador.id)).where(
                    SalaJugador.sala_id == sala_id
                )
            )

            db.session.commit()

            return jsonify({
                "ok": True,
                "mensaje": "Ya perteneces a esta sala.",
                "sala_id": sala_id,
                "anfitrion_id": sala.anfitrion_id,
                "jugadores": cantidad
            }), 200

        # No permitir entradas cuando la partida ya comenzo.
        if sala.estado == "en_curso":
            db.session.rollback()
            return respuesta_error(
                "No puedes entrar a una partida que ya esta en curso.",
                409
            )

        # Contar los participantes actuales.
        cantidad = db.session.scalar(
            select(func.count(SalaJugador.id)).where(
                SalaJugador.sala_id == sala_id
            )
        )

        # Impedir que ingresen mas de dos jugadores.
        if cantidad >= 2:
            db.session.rollback()
            return respuesta_error(
                "La sala ya tiene dos jugadores.",
                409
            )

        # Registrar al jugador.
        participacion = SalaJugador(
            sala_id=sala_id,
            usuario_id=usuario_id,
            listo=False
        )

        db.session.add(participacion)

        # El primer jugador se convierte en anfitrion.
        if sala.anfitrion_id is None:
            sala.anfitrion_id = usuario_id

        # La sala permanece esperando hasta iniciar la partida.
        sala.estado = "esperando"

        db.session.commit()

        return jsonify({
            "ok": True,
            "mensaje": "Te has unido correctamente a la sala.",
            "sala_id": sala_id,
            "anfitrion_id": sala.anfitrion_id,
            "jugadores": cantidad + 1
        }), 201

    except IntegrityError:
        db.session.rollback()
        return respuesta_error(
            "No fue posible registrar al jugador. "
            "Es posible que ya se encuentre en la sala.",
            409
        )


# -------------------------------------------------------------------
# Actividad 2: Transferencia voluntaria del anfitrion
# -------------------------------------------------------------------

@rooms_bp.route(
    "/salas/<int:sala_id>/transferir-anfitrion",
    methods=["POST"]
)
def transferir_anfitrion(sala_id):

    usuario_id = obtener_usuario_sesion()

    if usuario_id is None:
        return respuesta_error(
            "Debes iniciar sesion.",
            401
        )

    datos = request.get_json(silent=True) or {}

    try:
        nuevo_anfitrion_id = int(
            datos.get("nuevo_anfitrion_id")
        )
    except (TypeError, ValueError):
        return respuesta_error(
            "Debes indicar un jugador valido.",
            400
        )

    try:
        sala = obtener_sala_bloqueada(sala_id)

        if sala is None:
            db.session.rollback()
            return respuesta_error(
                "La sala no existe.",
                404
            )

        if sala.estado == "en_curso":
            db.session.rollback()
            return respuesta_error(
                "No se puede transferir el anfitrion durante una partida.",
                409
            )

        # Solamente el anfitrion actual puede transferir el rol.
        if sala.anfitrion_id != usuario_id:
            db.session.rollback()
            return respuesta_error(
                "Solamente el anfitrion actual puede transferir el rol.",
                403
            )

        # No permitir transferir el rol al mismo anfitrion.
        if nuevo_anfitrion_id == usuario_id:
            db.session.rollback()
            return respuesta_error(
                "Ya eres el anfitrion de esta sala.",
                400
            )

        # Verificar que el nuevo anfitrion pertenezca a la sala.
        nuevo_anfitrion = db.session.execute(
            select(SalaJugador).where(
                SalaJugador.sala_id == sala_id,
                SalaJugador.usuario_id == nuevo_anfitrion_id
            )
        ).scalar_one_or_none()

        if nuevo_anfitrion is None:
            db.session.rollback()
            return respuesta_error(
                "El jugador seleccionado no pertenece a esta sala.",
                404
            )

        sala.anfitrion_id = nuevo_anfitrion_id

        db.session.commit()

        return jsonify({
            "ok": True,
            "mensaje": "El rol de anfitrion se transfirio correctamente.",
            "anfitrion_id": nuevo_anfitrion_id
        }), 200

    except IntegrityError:
        db.session.rollback()
        return respuesta_error(
            "No fue posible transferir el rol de anfitrion.",
            409
        )


# -------------------------------------------------------------------
# Actividad 2: Salida de jugadores
# -------------------------------------------------------------------

@rooms_bp.route(
    "/salas/<int:sala_id>/salir",
    methods=["POST"]
)
def salir_sala(sala_id):

    usuario_id = obtener_usuario_sesion()

    if usuario_id is None:
        return respuesta_error(
            "Debes iniciar sesion.",
            401
        )

    try:
        sala = obtener_sala_bloqueada(sala_id)

        if sala is None:
            db.session.rollback()
            return respuesta_error(
                "La sala no existe.",
                404
            )

        # La salida durante la partida se coordinara con Persona 5.
        if sala.estado == "en_curso":
            db.session.rollback()
            return respuesta_error(
                "La salida durante una partida todavia no esta habilitada.",
                409
            )

        participacion = db.session.execute(
            select(SalaJugador).where(
                SalaJugador.sala_id == sala_id,
                SalaJugador.usuario_id == usuario_id
            )
        ).scalar_one_or_none()

        if participacion is None:
            db.session.rollback()
            return respuesta_error(
                "No perteneces a esta sala.",
                404
            )

        # Eliminar la participacion del jugador.
        db.session.delete(participacion)

        # Asegurar que la eliminacion se refleje antes de consultar.
        db.session.flush()

        # Obtener los jugadores restantes.
        restantes = db.session.execute(
            select(SalaJugador)
            .where(SalaJugador.sala_id == sala_id)
            .order_by(
                SalaJugador.fecha_union.asc(),
                SalaJugador.id.asc()
            )
        ).scalars().all()

        ids_restantes = [
            jugador.usuario_id
            for jugador in restantes
        ]

        # Si el anfitrion salio, asignar el rol al jugador restante.
        # Si no queda ninguno, el anfitrion pasa a ser NULL.
        if sala.anfitrion_id not in ids_restantes:
            sala.anfitrion_id = (
                restantes[0].usuario_id if restantes else None
            )

        # Actualizar el estado de la sala.
        if not restantes:
            sala.estado = "disponible"
        else:
            sala.estado = "esperando"

        db.session.commit()

        return jsonify({
            "ok": True,
            "mensaje": "Has salido de la sala correctamente.",
            "anfitrion_id": sala.anfitrion_id,
            "jugadores": len(restantes),
            "estado": sala.estado
        }), 200

    except IntegrityError:
        db.session.rollback()
        return respuesta_error(
            "No fue posible completar la salida de la sala.",
            409
        )
