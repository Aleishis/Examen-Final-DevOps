from sqlalchemy import CheckConstraint, Enum, ForeignKey, text
from extensions import db


class Usuario(db.Model):
    __tablename__ = "usuarios"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), nullable=False, unique=True)
    email = db.Column(db.String(255), nullable=False, unique=True)
    rol = db.Column(
    db.String(20),
    nullable=False,
    server_default="jugador",
    )
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(
        db.DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )


class Categoria(db.Model):
    __tablename__ = "categorias"

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False, unique=True)
    activa = db.Column(
        db.Boolean,
        nullable=False,
        server_default=text("1"),
    )
    portada_id = db.Column(
    db.Integer,
    ForeignKey(
        "parejas_cartas.id",
        name="fk_categorias_portada",
        ondelete="SET NULL",
        onupdate="CASCADE",
    ),
    nullable=True,
    )


class ParejaCarta(db.Model):
    __tablename__ = "parejas_cartas"

    id = db.Column(db.Integer, primary_key=True)
    categoria_id = db.Column(
        db.Integer,
        ForeignKey(
            "categorias.id",
            name="fk_parejas_categoria",
            ondelete="RESTRICT",
            onupdate="CASCADE",
        ),
        nullable=False,
    )
    nombre = db.Column(db.String(100), nullable=False)
    imagen = db.Column(db.String(500), nullable=False)


class Sala(db.Model):
    __tablename__ = "salas"

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50), nullable=False, unique=True)
    anfitrion_id = db.Column(
        db.Integer,
        ForeignKey(
            "usuarios.id",
            name="fk_salas_anfitrion",
            ondelete="SET NULL",
            onupdate="CASCADE",
        ),
        nullable=True,
    )
    categoria_id = db.Column(
        db.Integer,
        ForeignKey(
            "categorias.id",
            name="fk_salas_categoria",
            ondelete="RESTRICT",
            onupdate="CASCADE",
        ),
        nullable=False,
    )
    dificultad = db.Column(
    Enum("facil", "media", "dificil", name="dificultad_sala"),
    nullable=False,
    server_default=text("'facil'")
    )
    estado = db.Column(
        Enum(
            "disponible",
            "esperando",
            "en_curso",
            name="estado_sala",
        ),
        nullable=False,
        server_default=text("'disponible'"),
    )


class Partida(db.Model):
    __tablename__ = "partidas"

    id = db.Column(db.Integer, primary_key=True)
    sala_id = db.Column(
        db.Integer,
        ForeignKey(
            "salas.id",
            name="fk_partidas_sala",
            ondelete="RESTRICT",
            onupdate="CASCADE",
        ),
        nullable=False,
    )
    categoria_id = db.Column(
        db.Integer,
        ForeignKey(
            "categorias.id",
            name="fk_partidas_categoria",
            ondelete="RESTRICT",
            onupdate="CASCADE",
        ),
        nullable=False,
    )
    dificultad = db.Column(
    Enum("facil", "media", "dificil", name="dificultad_partida"),
    nullable=False,
    )
    jugador1_id = db.Column(
        db.Integer,
        ForeignKey(
            "usuarios.id",
            name="fk_partidas_jugador1",
            ondelete="RESTRICT",
            onupdate="CASCADE",
        ),
        nullable=False,
    )
    jugador2_id = db.Column(
        db.Integer,
        ForeignKey(
            "usuarios.id",
            name="fk_partidas_jugador2",
            ondelete="RESTRICT",
            onupdate="CASCADE",
        ),
        nullable=False,
    )
    puntuacion_jugador1 = db.Column(
        db.Integer,
        nullable=False,
        server_default=text("0"),
    )
    puntuacion_jugador2 = db.Column(
        db.Integer,
        nullable=False,
        server_default=text("0"),
    )
    ganador_id = db.Column(
        db.Integer,
        ForeignKey(
            "usuarios.id",
            name="fk_partidas_ganador",
            ondelete="SET NULL",
            onupdate="CASCADE",
        ),
        nullable=True,
    )
    fecha_inicio = db.Column(db.DateTime, nullable=False)
    fecha_fin = db.Column(db.DateTime, nullable=False)

    __table_args__ = (
        CheckConstraint(
            "puntuacion_jugador1 >= 0",
            name="chk_puntuacion_jugador1",
        ),
        CheckConstraint(
            "puntuacion_jugador2 >= 0",
            name="chk_puntuacion_jugador2",
        ),
        CheckConstraint(
            "fecha_fin >= fecha_inicio",
            name="chk_fechas_partida",
        ),
    )
