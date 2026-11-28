import os
import uuid
import json

from flask import (
    Blueprint,
    current_app,
    redirect,
    render_template,
    request,
    url_for,
    flash
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


# Delete selected categories
@categories_bp.route("/eliminar", methods=["POST"])
def delete_selected():
    selected_ids = request.form.getlist("categoria_ids")

    if not selected_ids:
        flash("Selecciona al menos una categoría para eliminar.")
        return redirect(url_for("categories.index"))

    # Validar los identificadores recibidos.
    try:
        category_ids = list(dict.fromkeys(
            int(value) for value in selected_ids
        ))

        if any(category_id <= 0 for category_id in category_ids):
            raise ValueError

    except (ValueError, TypeError):
        flash("La selección de categorías no es válida.")
        return redirect(url_for("categories.index"))

    categories = Categoria.query.filter(
        Categoria.id.in_(category_ids)
    ).all()

    if len(categories) != len(category_ids):
        flash(
            "Una o más categorías ya no existen. "
            "Actualiza el listado e inténtalo de nuevo."
        )
        return redirect(url_for("categories.index"))

    # Guardar las rutas de las imágenes para limpiarlas después
    # de confirmar la eliminación en la base de datos.
    image_paths = set()

    try:
        for category in categories:
            pairs = ParejaCarta.query.filter_by(
                categoria_id=category.id
            ).all()

            for pair in pairs:
                if pair.imagen:
                    image_paths.add(pair.imagen)

            # Primero quitar la referencia de la portada.
            category.portada_id = None

        # Aplicar el cambio de portada antes de eliminar las tarjetas.
        db.session.flush()

        # Eliminar primero todas las tarjetas de las categorías seleccionadas.
        for category in categories:
            pairs = ParejaCarta.query.filter_by(
                categoria_id=category.id
            ).all()

            for pair in pairs:
                db.session.delete(pair)

        # Aplicar la eliminación de las tarjetas antes de borrar las categorías.
        db.session.flush()

        # Ahora que las tarjetas ya fueron eliminadas, borrar las categorías.
        for category in categories:
            db.session.delete(category)

        db.session.commit()

    except Exception:
        db.session.rollback()

        current_app.logger.exception(
            "Error al eliminar las categorías seleccionadas."
        )

        flash(
            "No se pudieron eliminar las categorías. "
            "No se guardaron los cambios."
        )
        return redirect(url_for("categories.index"))

    # La eliminación en la base de datos ya se confirmó.
    # Solo borrar archivos que ninguna tarjeta siga utilizando.
    for image_path in image_paths:
        try:
            remove_unused_image(image_path)
        except OSError:
            current_app.logger.exception(
                "No se pudo eliminar la imagen: %s",
                image_path,
            )

    flash(
        f"Se eliminaron {len(categories)} categoría(s) correctamente."
    )

    return redirect(url_for("categories.index"))


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
    def render_create_page(error=None, status=200):
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
        ), status

    if request.method == "GET":
        return render_create_page()

    # Obtener y validar el nombre de la categoría.
    name = request.form.get("nombre", "").strip()

    if not name:
        return render_create_page(
            "Escribe el nombre de la categoría.", 400
        )

    if len(name) > 100:
        return render_create_page(
            "El nombre no puede superar los 100 caracteres.", 400
        )

    # Obtener los archivos seleccionados.
    files = [
        file
        for file in request.files.getlist("imagenes_tarjetas")
        if file and file.filename
    ]

    if len(files) > 50:
        return render_create_page(
            "No puedes agregar más de 50 tarjetas.", 400
        )

    # Leer los nombres y la portada enviados desde JavaScript.
    try:
        metadata = json.loads(
            request.form.get("tarjetas_metadata", "")
        )

        tarjetas_metadata = metadata["tarjetas"]
        portada_index = metadata["portada_index"]

        if not isinstance(tarjetas_metadata, list):
            raise ValueError("La lista de tarjetas no es válida.")

        if len(tarjetas_metadata) != len(files):
            raise ValueError(
                "La cantidad de imágenes no coincide con las tarjetas."
            )

        if portada_index is not None:
            if (
                not isinstance(portada_index, int)
                or isinstance(portada_index, bool)
                or not 0 <= portada_index < len(files)
            ):
                raise ValueError(
                    "La portada seleccionada no es válida."
                )

        nombres = []

        for tarjeta in tarjetas_metadata:
            if not isinstance(tarjeta, dict):
                raise ValueError(
                    "Los datos de una tarjeta no son válidos."
                )

            nombre = tarjeta.get("nombre")

            if not isinstance(nombre, str):
                raise ValueError(
                    "El nombre de una tarjeta no es válido."
                )

            nombre = nombre.strip()

            if not nombre:
                raise ValueError(
                    "Todas las tarjetas deben tener un nombre."
                )

            if len(nombre) > 100:
                raise ValueError(
                    "Los nombres de las tarjetas no pueden superar "
                    "los 100 caracteres."
                )

            nombres.append(nombre)

    except (ValueError, TypeError, KeyError):
        return render_create_page(
            "Los datos de las tarjetas no son válidos. "
            "Revisa las imágenes y sus nombres.", 400
        )

    # Archivos guardados durante esta operación.
    saved_paths = []

    try:
        # Crear la categoría dentro de la transacción.
        # Se activa únicamente si hay al menos 9 tarjetas.
        category = Categoria(
            nombre=name,
            activa=len(files) >= 9,
        )

        db.session.add(category)

        # Obtener el ID de la categoría sin confirmar la transacción.
        db.session.flush()

        # Guardar las imágenes y crear todas las tarjetas.
        parejas = []

        for file, nombre in zip(files, nombres):
            image_path = save_uploaded_image(file)
            saved_paths.append(image_path)

            pair = ParejaCarta(
                categoria_id=category.id,
                nombre=nombre,
                imagen=image_path,
            )

            db.session.add(pair)
            parejas.append(pair)

        # Obtener los IDs de las tarjetas antes de asignar la portada.
        db.session.flush()

        if portada_index is not None:
            portada = parejas[portada_index]
            category.portada_id = portada.id

        # Guardar categoría, tarjetas y portada en una sola transacción.
        db.session.commit()

    except IntegrityError:
        db.session.rollback()

        for image_path in saved_paths:
            remove_unused_image(image_path)

        return render_create_page(
            "Ya existe una categoría con ese nombre.", 400
        )

    except ValueError as exc:
        db.session.rollback()

        for image_path in saved_paths:
            remove_unused_image(image_path)

        return render_create_page(str(exc), 400)

    except Exception:
        db.session.rollback()

        for image_path in saved_paths:
            try:
                remove_unused_image(image_path)
            except OSError:
                current_app.logger.exception(
                    "No se pudo limpiar una imagen: %s",
                    image_path,
                )

        current_app.logger.exception(
            "Error al crear la categoría y sus tarjetas."
        )

        return render_create_page(
            "No se pudo crear la categoría. "
            "Revisa los datos e inténtalo de nuevo.", 500
        )

    # Abrir la categoría creada para revisar o editar sus tarjetas.
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

            count = ParejaCarta.query.filter_by(
                categoria_id=category.id
            ).count()

            # No permitir activar categorías sin dificultades disponibles
            if count < 9:
                active = False

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

        
        # Add multiple cards
        elif action == "add_pair":
            files = request.files.getlist("imagenes_tarjetas")

            # Ignorar archivos vacíos
            files = [file for file in files if file and file.filename]

            if not files:
                return render_edit_page(
                    category, "Selecciona al menos una imagen."
                ), 400

            current_count = ParejaCarta.query.filter_by(
                categoria_id=category.id
            ).count()

            if current_count + len(files) > 50:
                return render_edit_page(
                    category,
                    f"Solo puedes agregar {50 - current_count} "
                    "tarjetas más a esta categoría."
                ), 400

            saved_paths = []

            try:
                for file in files:
                    # Obtener el nombre del archivo sin su extensión
                    name = secure_filename(file.filename)
                    name = os.path.splitext(name)[0].strip()

                    if not name:
                        raise ValueError(
                            "Uno de los archivos no tiene un nombre válido."
                        )

                    if len(name) > 100:
                        raise ValueError(
                            f"El nombre del archivo '{name}' "
                            "supera los 100 caracteres."
                        )

                    image_path = save_uploaded_image(file)
                    saved_paths.append(image_path)

                    pair = ParejaCarta(
                        categoria_id=category.id,
                        nombre=name,
                        imagen=image_path,
                    )

                    db.session.add(pair)

                db.session.commit()

            except ValueError as exc:
                db.session.rollback()

                for image_path in saved_paths:
                    remove_unused_image(image_path)

                return render_edit_page(category, str(exc)), 400

            except Exception:
                db.session.rollback()

                for image_path in saved_paths:
                    remove_unused_image(image_path)

                current_app.logger.exception(
                    "Error al agregar las tarjetas"
                )

                return render_edit_page(
                    category, "No se pudieron agregar las tarjetas."
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