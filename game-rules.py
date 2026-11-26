# Archivo para funciones globales que se utilicen en el juego

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