from flask import Blueprint, render_template, request
from sqlalchemy import func
from sqlalchemy.orm import aliased

from extensions import db
from models import Categoria, ParejaCarta


categorias_bp = Blueprint(
    "categorias",
    __name__,
    url_prefix="/admin/categorias",
)


@categorias_bp.route("/")
def listar():
    # Alias para consultar la pareja elegida como portada.
    Portada = aliased(ParejaCarta)

    # Consulta categorías, portadas y cantidad de parejas.
    consulta = (
        db.session.query(
            Categoria,
            Portada.imagen.label("imagen_portada"),
            func.count(ParejaCarta.id).label("cantidad_parejas"),
        )
        .outerjoin(
            ParejaCarta,
            Categoria.id == ParejaCarta.categoria_id,
        )
        .outerjoin(
            Portada,
            Categoria.portada_id == Portada.id,
        )
        .group_by(
            Categoria.id,
            Portada.imagen,
        )
    )

    # Filtros recibidos desde el formulario.
    busqueda = request.args.get("q", "").strip()
    estado = request.args.get("estado", "todas")
    cantidad = request.args.get("cantidad", "todas")
    orden = request.args.get("orden", "nombre_asc")

    if busqueda:
        consulta = consulta.filter(
            Categoria.nombre.ilike(f"%{busqueda}%")
        )

    if estado == "activas":
        consulta = consulta.filter(Categoria.activa.is_(True))
    elif estado == "inactivas":
        consulta = consulta.filter(Categoria.activa.is_(False))

    conteo = func.count(ParejaCarta.id)

    if cantidad == "menos_9":
        consulta = consulta.having(conteo < 9)
    elif cantidad == "9_14":
        consulta = consulta.having(conteo.between(9, 14))
    elif cantidad == "15_24":
        consulta = consulta.having(conteo.between(15, 24))
    elif cantidad == "25_mas":
        consulta = consulta.having(conteo >= 25)

    if orden == "nombre_desc":
        consulta = consulta.order_by(Categoria.nombre.desc())
    elif orden == "parejas_asc":
        consulta = consulta.order_by(conteo.asc(), Categoria.nombre.asc())
    elif orden == "parejas_desc":
        consulta = consulta.order_by(conteo.desc(), Categoria.nombre.asc())
    else:
        consulta = consulta.order_by(Categoria.nombre.asc())

    resultados = consulta.all()

    categorias = []

    for categoria, imagen_portada, cantidad_parejas in resultados:
        categorias.append({
            "id": categoria.id,
            "nombre": categoria.nombre,
            "activa": categoria.activa,
            "portada": imagen_portada,
            "cantidad_parejas": cantidad_parejas,
            "dificultades": {
                "facil": cantidad_parejas >= 9,
                "media": cantidad_parejas >= 15,
                "dificil": cantidad_parejas >= 25,
            },
        })

    return render_template(
        "categories/categories.html",
        categorias=categorias,
        filtros={
            "q": busqueda,
            "estado": estado,
            "cantidad": cantidad,
            "orden": orden,
        },
    )
