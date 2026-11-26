# Archivo para funciones globales que pueden ser utiles para el crud, salas y logica del juego

# Función para obtener las dificultades disponibles según la cantidad de pares
def obtener_dificultades(cantidad_pares):
    dificultades = []

    if cantidad_pares >= 3:
        dificultades.append("facil")

    if cantidad_pares >= 6:
        dificultades.append("media")

    if cantidad_pares >= 10:
        dificultades.append("dificil")

    return dificultades

# Función para obtener la cantidad de parejas de una categoría
def contar_parejas_categoria(categoria_id):
    from main import db
    from models import ParejaCarta

    return db.session.query(ParejaCarta).filter_by(
        categoria_id=categoria_id
    ).count()