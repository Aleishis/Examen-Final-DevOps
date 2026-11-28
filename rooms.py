
from flask import Blueprint, render_template
from sqlalchemy import func

from extensions import db
from models import Sala, SalaJugador, Categoria, Usuario


# Blueprint encargado de las funcionalidades de las salas.
rooms_bp = Blueprint("rooms", __name__)


@rooms_bp.route("/salas", methods=["GET"])
def listar_salas():
    """
    Obtiene todas las salas registradas junto con su categoría
    y el usuario que tiene asignado el rol de anfitrión.
    """

    registros = (
        db.session.query(Sala, Categoria, Usuario)
        .join(Categoria, Categoria.id == Sala.categoria_id)
        .outerjoin(Usuario, Usuario.id == Sala.anfitrion_id)
        .order_by(Sala.id.asc())
        .all()
    )

    # Consultar la cantidad de jugadores registrados en cada sala.
    conteos = (
        db.session.query(
            SalaJugador.sala_id,
            func.count(SalaJugador.id)
        )
        .group_by(SalaJugador.sala_id)
        .all()
    )

    # Convertir los resultados en un diccionario:
    # {id_sala: cantidad_de_jugadores}
    jugadores_por_sala = {
        sala_id: cantidad
        for sala_id, cantidad in conteos
    }

    # Convertir los valores internos en etiquetas legibles.
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
