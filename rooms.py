
# -------------------------------------------------------------------
# Importaciones
# -------------------------------------------------------------------

from pathlib import Path
from importlib.util import module_from_spec, spec_from_file_location

from flask import (
    Blueprint,
    jsonify,
    render_template,
    request,
    session,
    redirect,
    url_for
)

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from extensions import db
from models import Sala, SalaJugador, Categoria, Usuario

from room_events import emitir_actualizacion_sala


rooms_bp = Blueprint("rooms", __name__)


# -------------------------------------------------------------------
# Carga de funciones compartidas de game-rules.py
# -------------------------------------------------------------------

ruta_reglas = Path(__file__).with_name("game-rules.py")

spec_reglas = spec_from_file_location(
    "game_rules",
    ruta_reglas
)

if spec_reglas is None or spec_reglas.loader is None:
    raise ImportError("No se pudo cargar game-rules.py")

modulo_reglas = module_from_spec(spec_reglas)
spec_reglas.loader.exec_module(modulo_reglas)

obtener_dificultades = modulo_reglas.obtener_dificultades
contar_parejas_categoria = modulo_reglas.contar_parejas_categoria


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

    if isinstance(valor, bool):
        return None

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


def obtener_participantes_bloqueados(sala_id):
    """
    Obtiene los participantes de una sala y bloquea sus registros
    durante la transaccion.
    """
    consulta = (
        select(SalaJugador)
        .where(SalaJugador.sala_id == sala_id)
        .order_by(
            SalaJugador.fecha_union.asc(),
            SalaJugador.id.asc()
        )
        .with_for_update()
    )

    return db.session.execute(consulta).scalars().all()


# -------------------------------------------------------------------
# Actividad 1: Listado de salas
# -------------------------------------------------------------------

@rooms_bp.route("/salas", methods=["GET"])
def listar_salas():

    # Identificar las salas en las que participa el usuario actual.
    usuario_id = obtener_usuario_sesion()

    salas_usuario = set()

    if usuario_id is not None:
        ids_salas = db.session.scalars(
            select(SalaJugador.sala_id).where(
                SalaJugador.usuario_id == usuario_id
            )
        ).all()

        salas_usuario = set(ids_salas)

    # Consultar las salas junto con su categoria y anfitrion.
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
            "jugadores": jugadores_por_sala.get(sala.id, 0),
            "pertenece": sala.id in salas_usuario
        })

    return render_template("rooms.html", salas=salas)


# -------------------------------------------------------------------
# Actividad 2: Pantalla de espera de una sala
# -------------------------------------------------------------------

@rooms_bp.route(
    "/salas/<int:sala_id>",
    methods=["GET"]
)
def ver_sala(sala_id):

    usuario_id = obtener_usuario_sesion()

    if usuario_id is None:
        return redirect(url_for("rooms.listar_salas"))

    sala = db.session.get(Sala, sala_id)

    if sala is None:
        return "La sala solicitada no existe.", 404

    # Obtener los jugadores registrados en la sala.
    participaciones = (
        db.session.query(SalaJugador, Usuario)
        .join(Usuario, Usuario.id == SalaJugador.usuario_id)
        .filter(SalaJugador.sala_id == sala_id)
        .order_by(
            SalaJugador.fecha_union.asc(),
            SalaJugador.id.asc()
        )
        .all()
    )

    # Comprobar que el usuario actual pertenezca a la sala.
    ids_jugadores = [
        participacion.usuario_id
        for participacion, usuario in participaciones
    ]

    if usuario_id not in ids_jugadores:
        return redirect(url_for("rooms.listar_salas"))

    # Preparar la informacion de los participantes.
    jugadores = []

    for participacion, usuario in participaciones:
        jugadores.append({
            "id": usuario.id,
            "username": usuario.username,
            "listo": participacion.listo
        })

    # Comprobar si ambos jugadores estan preparados.
    todos_listos = (
        len(participaciones) == 2
        and all(
            participacion.listo
            for participacion, usuario in participaciones
        )
    )

    # Consultar el estado de preparacion del usuario actual.
    mi_estado_listo = any(
        participacion.usuario_id == usuario_id
        and participacion.listo
        for participacion, usuario in participaciones
    )

    categoria = db.session.get(Categoria, sala.categoria_id)

    # Obtener categorias activas y sus dificultades disponibles.
    categorias_configurables = []

    categorias_activas = (
        Categoria.query
        .filter_by(activa=True)
        .order_by(Categoria.nombre.asc())
        .all()
    )

    for categoria_opcion in categorias_activas:

        cantidad_pares = contar_parejas_categoria(
            categoria_opcion.id
        )

        dificultades = obtener_dificultades(cantidad_pares)

        if dificultades:
            categorias_configurables.append({
                "id": categoria_opcion.id,
                "nombre": categoria_opcion.nombre,
                "cantidad_pares": cantidad_pares,
                "dificultades": dificultades
            })

    return render_template(
        "room_lobby.html",
        sala=sala,
        categoria=categoria,
        jugadores=jugadores,
        usuario_id=usuario_id,
        es_anfitrion=(sala.anfitrion_id == usuario_id),
        todos_listos=todos_listos,
        mi_estado_listo=mi_estado_listo,
        categorias_configurables=categorias_configurables
    )


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
        sala = obtener_sala_bloqueada(sala_id)

        if sala is None:
            db.session.rollback()
            return respuesta_error(
                "La sala solicitada no existe.",
                404
            )

        usuario = db.session.get(Usuario, usuario_id)

        if usuario is None:
            db.session.rollback()
            return respuesta_error(
                "El usuario de la sesion no existe.",
                401
            )

        participaciones = obtener_participantes_bloqueados(
            sala_id
        )

        # Comprobar si el usuario ya pertenece a la sala.
        participacion_existente = next(
            (
                participacion
                for participacion in participaciones
                if participacion.usuario_id == usuario_id
            ),
            None
        )

        if participacion_existente is not None:
            db.session.commit()

            return jsonify({
                "ok": True,
                "mensaje": "Ya perteneces a esta sala.",
                "sala_id": sala_id,
                "anfitrion_id": sala.anfitrion_id,
                "jugadores": len(participaciones)
            }), 200

        if sala.estado == "en_curso":
            db.session.rollback()
            return respuesta_error(
                "No puedes entrar a una partida que ya esta en curso.",
                409
            )

        if len(participaciones) >= 2:
            db.session.rollback()
            return respuesta_error(
                "La sala ya tiene dos jugadores.",
                409
            )

        # Reiniciar la preparacion de los jugadores existentes.
        for jugador in participaciones:
            jugador.listo = False

        # Registrar al nuevo jugador.
        nueva_participacion = SalaJugador(
            sala_id=sala_id,
            usuario_id=usuario_id,
            listo=False
        )

        db.session.add(nueva_participacion)

        ids_participantes = {
            jugador.usuario_id
            for jugador in participaciones
        }

        # Asignar o corregir el anfitrion.
        if (
            not participaciones
            or sala.anfitrion_id not in ids_participantes
        ):
            sala.anfitrion_id = (
                participaciones[0].usuario_id
                if participaciones
                else usuario_id
            )

        sala.estado = "esperando"

        db.session.commit()

        # Notificar a los participantes de la sala.
        emitir_actualizacion_sala(sala_id)

        return jsonify({
            "ok": True,
            "mensaje": "Te has unido correctamente a la sala.",
            "sala_id": sala_id,
            "anfitrion_id": sala.anfitrion_id,
            "jugadores": len(participaciones) + 1
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

    nuevo_anfitrion_recibido = datos.get(
        "nuevo_anfitrion_id"
    )

    if isinstance(nuevo_anfitrion_recibido, bool):
        return respuesta_error(
            "Debes indicar un jugador valido.",
            400
        )

    try:
        nuevo_anfitrion_id = int(
            nuevo_anfitrion_recibido
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

        if sala.anfitrion_id != usuario_id:
            db.session.rollback()
            return respuesta_error(
                "Solamente el anfitrion actual puede transferir el rol.",
                403
            )

        if nuevo_anfitrion_id == usuario_id:
            db.session.rollback()
            return respuesta_error(
                "Ya eres el anfitrion de esta sala.",
                400
            )

        participaciones = obtener_participantes_bloqueados(
            sala_id
        )

        ids_participantes = {
            jugador.usuario_id
            for jugador in participaciones
        }

        if nuevo_anfitrion_id not in ids_participantes:
            db.session.rollback()
            return respuesta_error(
                "El jugador seleccionado no pertenece a esta sala.",
                404
            )

        if usuario_id not in ids_participantes:
            db.session.rollback()
            return respuesta_error(
                "No perteneces a esta sala.",
                403
            )

        sala.anfitrion_id = nuevo_anfitrion_id

        db.session.commit()

        # Notificar el cambio de anfitrion.
        emitir_actualizacion_sala(sala_id)

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

        if sala.estado == "en_curso":
            db.session.rollback()
            return respuesta_error(
                "La salida durante una partida todavia no esta habilitada.",
                409
            )

        participaciones = obtener_participantes_bloqueados(
            sala_id
        )

        participacion = next(
            (
                jugador
                for jugador in participaciones
                if jugador.usuario_id == usuario_id
            ),
            None
        )

        if participacion is None:
            db.session.rollback()
            return respuesta_error(
                "No perteneces a esta sala.",
                404
            )

        # Eliminar la participacion del jugador.
        db.session.delete(participacion)
        db.session.flush()

        # Obtener los jugadores restantes.
        restantes = [
            jugador
            for jugador in participaciones
            if jugador.usuario_id != usuario_id
        ]

        # Reiniciar la preparacion de quienes permanecen.
        for jugador in restantes:
            jugador.listo = False

        ids_restantes = {
            jugador.usuario_id
            for jugador in restantes
        }

        # Transferir el anfitrion si es necesario.
        if sala.anfitrion_id not in ids_restantes:
            sala.anfitrion_id = (
                restantes[0].usuario_id if restantes else None
            )

        if not restantes:
            sala.estado = "disponible"
        else:
            sala.estado = "esperando"

        db.session.commit()

        # Notificar la salida y los cambios de la sala.
        emitir_actualizacion_sala(sala_id)

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


# -------------------------------------------------------------------
# Actividad 3: Gestion del estado de preparacion
# -------------------------------------------------------------------

@rooms_bp.route(
    "/salas/<int:sala_id>/listo",
    methods=["POST"]
)
def actualizar_estado_listo(sala_id):

    usuario_id = obtener_usuario_sesion()

    if usuario_id is None:
        return respuesta_error(
            "Debes iniciar sesion.",
            401
        )

    datos = request.get_json(silent=True)

    if (
        not isinstance(datos, dict)
        or not isinstance(datos.get("listo"), bool)
    ):
        return respuesta_error(
            "Debes indicar si estas listo o no.",
            400
        )

    nuevo_estado = datos["listo"]

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
                "La partida ya esta en curso.",
                409
            )

        participaciones = obtener_participantes_bloqueados(
            sala_id
        )

        participacion_usuario = next(
            (
                participacion
                for participacion in participaciones
                if participacion.usuario_id == usuario_id
            ),
            None
        )

        if participacion_usuario is None:
            db.session.rollback()
            return respuesta_error(
                "No perteneces a esta sala.",
                403
            )

        if len(participaciones) != 2:
            db.session.rollback()
            return respuesta_error(
                "Se necesitan dos jugadores para marcar "
                "la sala como lista.",
                409
            )

        participacion_usuario.listo = nuevo_estado

        todos_listos = all(
            participacion.listo
            for participacion in participaciones
        )

        db.session.commit()

        # Notificar los cambios en la preparacion.
        emitir_actualizacion_sala(sala_id)

        mensaje = (
            "Ambos jugadores estan listos. "
            "La sala esta preparada para comenzar."
            if todos_listos
            else "Tu estado de preparacion se actualizo correctamente."
        )

        return jsonify({
            "ok": True,
            "mensaje": mensaje,
            "listo": nuevo_estado,
            "todos_listos": todos_listos
        }), 200

    except IntegrityError:
        db.session.rollback()
        return respuesta_error(
            "No fue posible actualizar el estado de preparacion.",
            409
        )


# -------------------------------------------------------------------
# Actividad 4: Seleccion de categoria y dificultad
# -------------------------------------------------------------------

@rooms_bp.route(
    "/salas/<int:sala_id>/configuracion",
    methods=["POST"]
)
def actualizar_configuracion(sala_id):

    usuario_id = obtener_usuario_sesion()

    if usuario_id is None:
        return respuesta_error(
            "Debes iniciar sesion.",
            401
        )

    datos = request.get_json(silent=True)

    if not isinstance(datos, dict):
        return respuesta_error(
            "Debes proporcionar la configuracion.",
            400
        )

    # Validar el identificador de la categoria.
    categoria_recibida = datos.get("categoria_id")

    if isinstance(categoria_recibida, bool):
        return respuesta_error(
            "El identificador de la categoria no es valido.",
            400
        )

    if isinstance(categoria_recibida, int):
        categoria_id = categoria_recibida

    elif (
        isinstance(categoria_recibida, str)
        and categoria_recibida.strip().isdigit()
    ):
        categoria_id = int(categoria_recibida.strip())

    else:
        return respuesta_error(
            "El identificador de la categoria no es valido.",
            400
        )

    dificultad = datos.get("dificultad")

    dificultades_validas = {
        "facil",
        "media",
        "dificil"
    }

    if (
        not isinstance(dificultad, str)
        or dificultad not in dificultades_validas
    ):
        return respuesta_error(
            "La dificultad seleccionada no es valida.",
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
                "No puedes modificar una partida que ya esta en curso.",
                409
            )

        if sala.anfitrion_id != usuario_id:
            db.session.rollback()
            return respuesta_error(
                "Solamente el anfitrion puede cambiar "
                "la categoria y dificultad.",
                403
            )

        participaciones = obtener_participantes_bloqueados(
            sala_id
        )

        anfitrion_pertenece = any(
            jugador.usuario_id == usuario_id
            for jugador in participaciones
        )

        if not anfitrion_pertenece:
            db.session.rollback()
            return respuesta_error(
                "No perteneces a esta sala.",
                403
            )

        categoria = db.session.get(
            Categoria,
            categoria_id
        )

        if categoria is None:
            db.session.rollback()
            return respuesta_error(
                "La categoria seleccionada no existe.",
                404
            )

        if not categoria.activa:
            db.session.rollback()
            return respuesta_error(
                "La categoria seleccionada no esta disponible.",
                409
            )

        cantidad_pares = contar_parejas_categoria(
            categoria_id
        )

        dificultades_disponibles = obtener_dificultades(
            cantidad_pares
        )

        if not dificultades_disponibles:
            db.session.rollback()
            return respuesta_error(
                "La categoria no tiene suficientes parejas "
                "para iniciar una partida.",
                409
            )

        if dificultad not in dificultades_disponibles:
            db.session.rollback()
            return respuesta_error(
                "La dificultad seleccionada no esta disponible "
                "para esta categoria.",
                400
            )

        # Comprobar si realmente cambio la configuracion.
        configuracion_modificada = (
            sala.categoria_id != categoria_id
            or sala.dificultad != dificultad
        )

        sala.categoria_id = categoria_id
        sala.dificultad = dificultad

        # Reiniciar preparacion solamente si hubo cambios.
        if configuracion_modificada:
            for jugador in participaciones:
                jugador.listo = False

        db.session.commit()

        # Notificar un cambio real de configuracion.
        if configuracion_modificada:
            emitir_actualizacion_sala(sala_id)

        return jsonify({
            "ok": True,
            "mensaje": "La configuracion de la sala se actualizo correctamente.",
            "categoria_id": categoria.id,
            "categoria": categoria.nombre,
            "cantidad_pares": cantidad_pares,
            "dificultad": dificultad,
            "dificultades_disponibles": dificultades_disponibles,
            "configuracion_modificada": configuracion_modificada
        }), 200

    except IntegrityError:
        db.session.rollback()
        return respuesta_error(
            "No fue posible actualizar la configuracion de la sala.",
            409
        )
