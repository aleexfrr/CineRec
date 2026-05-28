"""
Crea los índices de todas las colecciones.
Ejecutar una sola vez al arrancar el proyecto:
    python -m app.setup_db
"""
import asyncio
import pymongo
from app.database import usuarios, valoraciones, peliculas, db


async def crear_indices():

    # ── USUARIOS ──────────────────────────────────────────────────────────────
    # email único: no puede haber dos usuarios con el mismo correo
    await usuarios.create_index("email", unique=True)

    # ── VALORACIONES ─────────────────────────────────────────────────────────
    # un usuario solo puede valorar una película una vez
    await valoraciones.create_index(
        [("user_id", pymongo.ASCENDING), ("movie_id", pymongo.ASCENDING)],
        unique=True
    )
    # para buscar rápido todas las valoraciones de una película
    await valoraciones.create_index("movie_id")

    # ── PELICULAS ─────────────────────────────────────────────────────────────
    # búsqueda por texto en el título
    await peliculas.create_index([("title", pymongo.TEXT)])
    # filtrar por género
    await peliculas.create_index("genres")

    # ── DATASETS MOVIELENS ───────────────────────────────────────────────────
    ml_ratings = db["ml_ratings"]
    ml_tags    = db["ml_tags"]

    # misma lógica que valoraciones: un usuario, una nota por película
    await ml_ratings.create_index(
        [("user_id", pymongo.ASCENDING), ("movie_id", pymongo.ASCENDING)],
        unique=True
    )
    await ml_ratings.create_index("movie_id")

    await ml_tags.create_index([("user_id", pymongo.ASCENDING), ("movie_id", pymongo.ASCENDING)])
    await ml_tags.create_index("movie_id")

    # genome: buscar todos los tags relevantes de una película
    ml_genome_scores = db["ml_genome_scores"]
    await ml_genome_scores.create_index("movie_id")
    await ml_genome_scores.create_index("tag_id")

    print("Índices creados correctamente")


if __name__ == "__main__":
    asyncio.run(crear_indices())
