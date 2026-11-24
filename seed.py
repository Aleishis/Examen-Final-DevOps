import os

from werkzeug.security import generate_password_hash

from main import app, db
from models import Categoria, ParejaCarta, Sala, Usuario


# Datos iniciales del juego
CATEGORIAS = {
    "creepypastas": [
        ("Ben Drowned", "images/creepypastas/Ben Drowned.png"),
        ("Bloody Painter", "images/creepypastas/Bloody Painter.png"),
        ("clockwork", "images/creepypastas/clockwork.png"),
        ("Dead Bart", "images/creepypastas/Dead Bart.png"),
        ("Eyeless Jack", "images/creepypastas/Eyeless Jack.png"),
        ("Herobrine", "images/creepypastas/Herobrine.png"),
        ("Homicidal Liu", "images/creepypastas/Homicidal Liu.png"),
        ("hoodie", "images/creepypastas/hoodie.png"),
        ("Jane the Killer", "images/creepypastas/Jane the Killer.png"),
        ("Jeff the Killer", "images/creepypastas/Jeff the Killer.png"),
        ("Laughing Jack", "images/creepypastas/Laughing Jack.png"),
        ("masky", "images/creepypastas/masky.png"),
        ("sally", "images/creepypastas/sally.png"),
        ("Siren Head", "images/creepypastas/Siren Head.png"),
        ("Slender Man", "images/creepypastas/Slenderman.png"),
        ("Smile Dog", "images/creepypastas/Smile Dog.png"),
        ("Sonic exe", "images/creepypastas/Sonic exe.png"),
        ("Suicidio de Calamardo", "images/creepypastas/Suicidio de Calamardo.png"),
        ("Tails Doll", "images/creepypastas/Tails Doll.png"),
        ("The Rake", "images/creepypastas/The Rake.png"),
        ("ticcy toby", "images/creepypastas/ticcy toby.png"),
        ("Zake", "images/creepypastas/Zake.png"),
    ],
    "Frutas": [
        ("Aguacate", "images/frutas/Aguacate.png"),
        ("Banana", "images/frutas/Banana.png"),
        ("Carambola", "images/frutas/Carambola.png"),
        ("Cereza", "images/frutas/Cereza.png"),
        ("Chile", "images/frutas/Chile.png"),
        ("Ciruela", "images/frutas/Ciruela.png"),
        ("Coco", "images/frutas/Coco.png"),
        ("Dragon", "images/frutas/Dragon.png"),
        ("Durazno", "images/frutas/Durazno.png"),
        ("Frambuesa", "images/frutas/Frambuesa.png"),
        ("Fresa", "images/frutas/Fresa.png"),
        ("Kiwi", "images/frutas/Kiwi.png"),
        ("Limon", "images/frutas/Limon.png"),
        ("Limoncito", "images/frutas/Limoncito.png"),
        ("Manzana", "images/frutas/Manzana.png"),
        ("Melon", "images/frutas/Melon.png"),
        ("Mora", "images/frutas/Mora.png"),
        ("Naranja", "images/frutas/Naranja.png"),
        ("nosejaja", "images/frutas/nosejaja.png"),
        ("Papaya", "images/frutas/Papaya.png"),
        ("Pera", "images/frutas/Pera.png"),
        ("Peraotravez", "images/frutas/Peraotravez.png"),
        ("Pina", "images/frutas/Pina.png"),
        ("Sandia", "images/frutas/Sandia.png"),
        ("Uva", "images/frutas/Uva.png"),
    ],
    "Dragon Ball": [
        ("beerus", "images/dragon ball/beerus.png"),
        ("black", "images/dragon ball/black.png"),
        ("broly", "images/dragon ball/broly.png"),
        ("bulma", "images/dragon ball/bulma.png"),
        ("caulifla", "images/dragon ball/caulifla.png"),
        ("dieciocho", "images/dragon ball/dieciocho.png"),
        ("freezer", "images/dragon ball/freezer.png"),
        ("gogeta", "images/dragon ball/gogeta.png"),
        ("gohan", "images/dragon ball/gohan.png"),
        ("goku", "images/dragon ball/goku.png"),
        ("kirillin", "images/dragon ball/kirillin.png"),
        ("launch", "images/dragon ball/launch.png"),
        ("milk", "images/dragon ball/milk.png"),
        ("pan", "images/dragon ball/pan.png"),
        ("piccolo", "images/dragon ball/piccolo.png"),
        ("roshi", "images/dragon ball/roshi.png"),
        ("trunks", "images/dragon ball/trunks.png"),
        ("vegeta", "images/dragon ball/vegeta.png"),
        ("vegetto", "images/dragon ball/vegetto.png"),
        ("videl", "images/dragon ball/videl.png"),
    ],
    "Paw Patrol": [
        ("apollo", "images/paw patrol/apollo.png"),
        ("chase", "images/paw patrol/chase.png"),
        ("everest", "images/paw patrol/everest.png"),
        ("marshall", "images/paw patrol/marshall.png"),
        ("rocky", "images/paw patrol/rocky.png"),
        ("rubble", "images/paw patrol/rubble.png"),
        ("skye", "images/paw patrol/skye.png"),
        ("tracker", "images/paw patrol/tracker.png"),
        ("zuma", "images/paw patrol/zuma.png"),
    ],
    "Sanrio": [
        ("angel 1", "images/sanrio/angel 1.png"),
        ("angel 2", "images/sanrio/angel 2.png"),
        ("donald", "images/sanrio/donald.png"),
        ("hello kitty", "images/sanrio/hello kitty.png"),
        ("keroppi", "images/sanrio/keroppi.png"),
        ("kuromi", "images/sanrio/kuromi.png"),
        ("melody", "images/sanrio/melody.png"),
        ("perro", "images/sanrio/perro.png"),
        ("pez", "images/sanrio/pez.png"),
        ("picos", "images/sanrio/picos.png"),
        ("pingu", "images/sanrio/pingu.png"),
        ("pompurin", "images/sanrio/pompurin.png"),
    ],
    "Vocaloid": [
        ("defoko", "images/vocaloid/defoko.png"),
        ("flower", "images/vocaloid/flower.png"),
        ("frimomen", "images/vocaloid/frimomen.png"),
        ("fukase", "images/vocaloid/fukase.png"),
        ("gakupo", "images/vocaloid/gakupo.png"),
        ("gumi", "images/vocaloid/gumi.png"),
        ("IA", "images/vocaloid/IA.png"),
        ("jun", "images/vocaloid/jun.png"),
        ("kaito", "images/vocaloid/kaito.png"),
        ("kazehiki", "images/vocaloid/kazehiki.png"),
        ("kiyoteru", "images/vocaloid/kiyoteru.png"),
        ("len", "images/vocaloid/len.png"),
        ("luka", "images/vocaloid/luka.png"),
        ("meiko", "images/vocaloid/meiko.png"),
        ("miku", "images/vocaloid/miku.png"),
        ("neru", "images/vocaloid/neru.png"),
        ("oliver", "images/vocaloid/oliver.png"),
        ("rin", "images/vocaloid/rin.png"),
        ("ritsu", "images/vocaloid/ritsu.png"),
        ("ruko", "images/vocaloid/ruko.png"),
        ("tei", "images/vocaloid/tei.png"),
        ("teto", "images/vocaloid/teto.png"),
        ("una", "images/vocaloid/una.png"),
        ("vy2", "images/vocaloid/vy2.png"),
        ("yuki", "images/vocaloid/yuki.png"),
    ],
}

SALAS = [
    "Sala 1",
    "Sala 2",
    "Sala 3",
]


def seed_database():
    with app.app_context():
        try:
            # 1. Crear las categorías que todavía no existan
            categorias_db = {}

            for nombre in CATEGORIAS:
                categoria = Categoria.query.filter_by(
                    nombre=nombre
                ).first()

                if categoria is None:
                    categoria = Categoria(nombre=nombre)
                    db.session.add(categoria)
                    db.session.flush()

                categorias_db[nombre] = categoria

            # 2. Crear las parejas de cartas faltantes
            for nombre_categoria, parejas in CATEGORIAS.items():
                categoria = categorias_db[nombre_categoria]

                for nombre, imagen in parejas:
                    pareja = ParejaCarta.query.filter_by(
                        categoria_id=categoria.id,
                        nombre=nombre,
                    ).first()

                    if pareja is None:
                        db.session.add(
                            ParejaCarta(
                                categoria_id=categoria.id,
                                nombre=nombre,
                                imagen=imagen,
                            )
                        )

            # Guardar categorías y parejas antes de crear salas
            db.session.flush()

            # 3. Crear las salas con los nombres definidos en SALAS
            # Todas comienzan con la primera categoría disponible.
            categoria_inicial = next(iter(categorias_db.values()))

            for nombre_sala in SALAS:
                sala = Sala.query.filter_by(
                    nombre=nombre_sala
                ).first()

                if sala is None:
                    db.session.add(
                        Sala(
                            nombre=nombre_sala,
                            categoria_id=categoria_inicial.id,
                            estado="disponible",
                        )
                    )

            # 4. Crear un usuario administrador inicial si no existe
            # Crear el administrador si todavía no existe
            admin_username = os.getenv("ADMIN_USERNAME", "admin")
            admin_email = os.getenv("ADMIN_EMAIL", "admin@memorama.local")
            admin_password = os.getenv("ADMIN_PASSWORD")

            if not admin_password:
                raise ValueError(
                    "Debes configurar ADMIN_PASSWORD en el archivo .env"
                )

            admin = Usuario.query.filter_by(
                username=admin_username
            ).first()

            if admin is None:
                admin = Usuario(
                    username=admin_username,
                    email=admin_email,
                    password_hash=generate_password_hash(admin_password),
                    rol="admin",
                )
                db.session.add(admin)

            # Guardar todos los cambios
            db.session.commit()
            print("Datos iniciales cargados correctamente.")

        except Exception:
            db.session.rollback()
            raise


if __name__ == "__main__":
    seed_database()
