import os
import uuid

from flask import (
    Blueprint,
    current_app,
    redirect,
    render_template,
    request,
    url_for,
)
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import aliased
from werkzeug.utils import secure_filename

from extensions import db
from models import Categoria, ParejaCarta


categories_bp = Blueprint(
    "categories",
    __name__,
    url_prefix="/admin/categorias",
)


ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "gif"}


def save_uploaded_image(file):
    """Guarda una imagen y devuelve su ruta relativa."""
    if not file or not file.filename:
        raise ValueError("Selecciona una imagen.")

    original_name = secure_filename(file.filename)

    if "." not in original_name:
        raise ValueError("El archivo no tiene una extensión válida.")

    extension = original_name.rsplit(".", 1)[-1].lower()

    if extension not in ALLOWED_EXTENSIONS:
        raise ValueError(
            "Formato no permitido. Usa PNG, JPG, JPEG, WEBP o GIF."
        )

    upload_folder = current_app.config["UPLOAD_FOLDER"]
    os.makedirs(upload_folder, exist_ok=True)

    filename = f"{uuid.uuid4().hex}.{extension}"
    file.save(os.path.join(upload_folder, filename))

    return f"uploads/{filename}"


def remove_unused_image(image_path):
    """Elimina el archivo solo si ninguna tarjeta lo utiliza."""
    if not image_path:
        return

    still_used = ParejaCarta.query.filter_by(
        imagen=image_path
    ).first()

    if still_used:
        return

    upload_folder = current_app.config["UPLOAD_FOLDER"]
    filename = os.path.basename(image_path)
    file_path = os.path.join(upload_folder, filename)

    if os.path.isfile(file_path):
        os.remove(file_path)


# List categories
@categories_bp.route("/")
def index():
    Cover = aliased(ParejaCarta)

    query = (
        db.session.query(
            Categoria,
            Cover.imagen.label("cover_image"),
            func.count(ParejaCarta.id).label("pair_count"),
        )
        .outerjoin(
            ParejaCarta,
            Categoria.id == ParejaCarta.categoria_id,
        )
        .outerjoin(
            Cover,
            Categoria.portada_id == Cover.id,
        )
        .group_by(
            Categoria.id,
            Cover.imagen,
        )
    )

    search = request.args.get("q", "").strip()
    status = request.args.get("estado", "todas")
    pair_count_filter = request.args.get("cantidad", "todas")
    order = request.args.get("orden", "nombre_asc")

    if search:
        query = query.filter(
            Categoria.nombre.ilike(f"%{search}%")
        )

    if status == "activas":
        query = query.filter(Categoria.activa.is_(True))
    elif status == "inactivas":
        query = query.filter(Categoria.activa.is_(False))

    count_expression = func.count(ParejaCarta.id)

    if pair_count_filter == "menos_9":
        query = query.having(count_expression < 9)
    elif pair_count_filter == "9_14":
        query = query.having(count_expression.between(9, 14))
    elif pair_count_filter == "15_24":
        query = query.having(count_expression.between(15, 24))
    elif pair_count_filter == "25_mas":
        query = query.having(count_expression >= 25)

    if order == "nombre_desc":
        query = query.order_by(Categoria.nombre.desc())
    elif order == "parejas_asc":
        query = query.order_by(
            count_expression.asc(),
            Categoria.nombre.asc(),
        )
    elif order == "parejas_desc":
        query = query.order_by(
            count_expression.desc(),
            Categoria.nombre.asc(),
        )
    else:
        query = query.order_by(Categoria.nombre.asc())

    results = query.all()
    categories = []

    for category, cover_image, pair_count in results:
        categories.append({
            "id": category.id,
            "nombre": category.nombre,
            "activa": category.activa,
            "portada": cover_image,
            "cantidad_parejas": pair_count,
            "dificultades": {
                "facil": pair_count >= 9,
                "media": pair_count >= 15,
                "dificil": pair_count >= 25,
            },
        })

    return render_template(
        "categories/index.html",
        categorias=categories,
        filtros={
            "q": search,
            "estado": status,
            "cantidad": pair_count_filter,
            "orden": order,
        },
    )


# Show category details
@categories_bp.route("/<int:categoria_id>")
def form(categoria_id):
    category = db.get_or_404(Categoria, categoria_id)

    pairs = (
        ParejaCarta.query
        .filter_by(categoria_id=category.id)
        .order_by(ParejaCarta.nombre.asc())
        .all()
    )

    pair_count = len(pairs)

    cover = next(
        (pair for pair in pairs if pair.id == category.portada_id),
        None,
    )

    difficulties = {
        "facil": pair_count >= 9,
        "media": pair_count >= 15,
        "dificil": pair_count >= 25,
    }

    return render_template(
        "categories/form.html",
        modo="ver",
        categoria=category,
        parejas=pairs,
        portada=cover,
        cantidad_parejas=pair_count,
        dificultades=difficulties,
        error=None,
    )
# Create a category
@categories_bp.route("/nueva", methods=["GET", "POST"])
def create():
    if request.method == "GET":
        return render_template(
            "categories/form.html",
            modo="crear",
            categoria=None,
            parejas=[],
            portada=None,
            cantidad_parejas=0,
            dificultades={
                "facil": False,
                "media": False,
                "dificil": False,
            },
            error=None,
        )

    name = request.form.get("nombre", "").strip()
    active = request.form.get("activa") == "on"

    if not name:
        error = "Escribe el nombre de la categoría."
    elif len(name) > 100:
        error = "El nombre no puede superar los 100 caracteres."
    else:
        error = None

    if error:
        return render_template(
            "categories/form.html",
            modo="crear",
            categoria=None,
            parejas=[],
            portada=None,
            cantidad_parejas=0,
            dificultades={
                "facil": False,
                "media": False,
                "dificil": False,
            },
            error=error,
        ), 400

    category = Categoria(nombre=name, activa=active)
    db.session.add(category)

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()

        return render_template(
            "categories/form.html",
            modo="crear",
            categoria=None,
            parejas=[],
            portada=None,
            cantidad_parejas=0,
            dificultades={
                "facil": False,
                "media": False,
                "dificil": False,
            },
            error="Ya existe una categoría con ese nombre.",
        ), 400

    return redirect(
        url_for("categories.edit", categoria_id=category.id)
    )


@categories_bp.route("/<int:categoria_id>/editar", methods=["GET", "POST"])
def edit(categoria_id):
    category = db.get_or_404(Categoria, categoria_id)

    if request.method == "POST":
        action = request.form.get("action")

        # Save category details
        if action == "save_details":
            name = request.form.get("nombre", "").strip()
            active = request.form.get("activa") == "on"

            if not name:
                return render_edit_page(
                    category, "El nombre es obligatorio."
                ), 400

            if len(name) > 100:
                return render_edit_page(
                    category, "El nombre no puede superar los 100 caracteres."
                ), 400

            category.nombre = name
            category.activa = active

            try:
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
                return render_edit_page(
                    category, "Ya existe una categoría con ese nombre."
                ), 400



        # Set or remove category cover
        elif action == "set_cover":
            try:
                pair_id = int(request.form.get("pareja_id", ""))
            except (ValueError, TypeError):
                return render_edit_page(
                    category, "La tarjeta seleccionada no es válida."
                ), 400

            pair = ParejaCarta.query.filter_by(
                id=pair_id,
                categoria_id=category.id,
            ).first()

            if not pair:
                return render_edit_page(
                    category,
                    "La tarjeta no existe en esta categoría.",
                ), 404

            if request.form.get("portada") == "on":
                category.portada_id = pair.id
            elif category.portada_id == pair.id:
                category.portada_id = None

            try:
                db.session.commit()
            except Exception:
                db.session.rollback()
                current_app.logger.exception(
                    "Error al cambiar la portada de la categoría"
                )
                return render_edit_page(
                    category, "No se pudo cambiar la portada."
                ), 500

        # Add one card
        elif action == "add_pair":
            name = request.form.get("nombre_tarjeta", "").strip()
            file = request.files.get("imagen_tarjeta")

            current_count = ParejaCarta.query.filter_by(
                categoria_id=category.id
            ).count()

            if current_count >= 50:
                return render_edit_page(
                    category, "No puedes agregar más de 50 tarjetas."
                ), 400

            if not name:
                return render_edit_page(
                    category, "Escribe el nombre de la tarjeta."
                ), 400

            if len(name) > 100:
                return render_edit_page(
                    category, "El nombre de la tarjeta no puede superar los 100 caracteres."
                ), 400

            if not file or not file.filename:
                return render_edit_page(
                    category, "Selecciona una imagen."
                ), 400

            image_path = None

            try:
                image_path = save_uploaded_image(file)

                pair = ParejaCarta(
                    categoria_id=category.id,
                    nombre=name,
                    imagen=image_path,
                )
                db.session.add(pair)
                db.session.commit()

            except ValueError as exc:
                db.session.rollback()

                if image_path:
                    remove_unused_image(image_path)

                return render_edit_page(category, str(exc)), 400

            except Exception:
                db.session.rollback()

                if image_path:
                    remove_unused_image(image_path)

                current_app.logger.exception("Error al agregar la tarjeta")

                return render_edit_page(
                    category, "No se pudo agregar la tarjeta."
                ), 500


        # Rename one card
        elif action == "rename_pair":
            try:
                pair_id = int(request.form.get("pareja_id", ""))
            except (ValueError, TypeError):
                return render_edit_page(
                    category,
                    "El identificador de la tarjeta no es válido.",
                ), 400

            pair = ParejaCarta.query.filter_by(
                id=pair_id,
                categoria_id=category.id,
            ).first()

            if not pair:
                return render_edit_page(
                    category,
                    "La tarjeta no existe en esta categoría.",
                ), 404

            new_name = request.form.get("nombre", "").strip()

            if not new_name:
                return render_edit_page(
                    category,
                    "El nombre de la tarjeta no puede estar vacío.",
                ), 400

            if len(new_name) > 100:
                return render_edit_page(
                    category,
                    "El nombre no puede superar los 100 caracteres.",
                ), 400

            pair.nombre = new_name

            try:
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
                return render_edit_page(
                    category,
                    "No se pudo guardar el nombre de la tarjeta.",
                ), 400

            return redirect(
                url_for("categories.edit", categoria_id=category.id)
            )

        # Delete multiple cards
        elif action == "delete_pairs":
            selected_values = request.form.getlist(
                "parejas_seleccionadas"
            )

            if not selected_values:
                return render_edit_page(
                    category,
                    "Selecciona al menos una tarjeta para eliminar.",
                ), 400

            # Convertir los identificadores y rechazar valores inválidos.
            try:
                selected_ids = list(dict.fromkeys(
                    int(value) for value in selected_values
                ))
            except (ValueError, TypeError):
                return render_edit_page(
                    category,
                    "La selección contiene identificadores no válidos.",
                ), 400

            if any(pair_id <= 0 for pair_id in selected_ids):
                return render_edit_page(
                    category,
                    "La selección contiene identificadores no válidos.",
                ), 400

            # Buscar exclusivamente tarjetas de esta categoría.
            selected_pairs = ParejaCarta.query.filter(
                ParejaCarta.categoria_id == category.id,
                ParejaCarta.id.in_(selected_ids),
            ).all()

            # Si falta alguna, no borrar ninguna.
            if len(selected_pairs) != len(selected_ids):
                return render_edit_page(
                    category,
                    "Una o más tarjetas no pertenecen a esta categoría "
                    "o ya no existen.",
                ), 400

            old_images = [pair.imagen for pair in selected_pairs]
            selected_id_set = set(selected_ids)

            try:
                # Quitar la portada si está entre las tarjetas seleccionadas.
                if category.portada_id in selected_id_set:
                    category.portada_id = None
                    db.session.flush()

                # Eliminar todas las tarjetas seleccionadas.
                for pair in selected_pairs:
                    db.session.delete(pair)

                db.session.commit()

            except Exception:
                db.session.rollback()
                current_app.logger.exception(
                    "Error al eliminar varias tarjetas"
                )

                return render_edit_page(
                    category,
                    "No se pudieron eliminar las tarjetas seleccionadas.",
                ), 500

            # Limpiar las imágenes que ya no estén siendo utilizadas.
            for image_path in old_images:
                try:
                    remove_unused_image(image_path)
                except OSError:
                    current_app.logger.exception(
                        "No se pudo eliminar el archivo de imagen: %s",
                        image_path,
                    )
        # Delete one card
        elif action == "delete_pair":
            try:
                pair_id = int(request.form.get("pareja_id", ""))
            except ValueError:
                return render_edit_page(
                    category, "La tarjeta seleccionada no es válida."
                ), 400

            pair = ParejaCarta.query.filter_by(
                id=pair_id,
                categoria_id=category.id,
            ).first()

            if not pair:
                return render_edit_page(
                    category, "La tarjeta no existe en esta categoría."
                ), 404

            old_image = pair.imagen

            if category.portada_id == pair.id:
                category.portada_id = None

            db.session.delete(pair)
            db.session.flush()

            try:
                db.session.commit()
            except Exception:
                db.session.rollback()
                current_app.logger.exception("Error al eliminar la tarjeta")

                return render_edit_page(
                    category, "No se pudo eliminar la tarjeta."
                ), 500

            remove_unused_image(old_image)

        else:
            return render_edit_page(
                category, "La operación solicitada no es válida."
            ), 400

        return redirect(
            url_for("categories.edit", categoria_id=category.id)
        )

    return render_edit_page(category)


def render_edit_page(category, error=None):
    pairs = (
        ParejaCarta.query
        .filter_by(categoria_id=category.id)
        .order_by(ParejaCarta.nombre.asc())
        .all()
    )

    cover = next(
        (pair for pair in pairs if pair.id == category.portada_id),
        None,
    )

    count = len(pairs)

    return render_template(
        "categories/form.html",
        modo="editar",
        categoria=category,
        parejas=pairs,
        portada=cover,
        cantidad_parejas=count,
        dificultades={
            "facil": count >= 9,
            "media": count >= 15,
            "dificil": count >= 25,
        },
        error=error,
    )