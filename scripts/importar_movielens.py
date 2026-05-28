"""
Importa los 6 CSV de MovieLens (ml-latest) a MongoDB.
Uso:
    python scripts/importar_movielens.py --carpeta /ruta/a/ml-latest

Ficheros que necesita:
    movies.csv          → colección 'peliculas'
    links.csv           → añade imdbId/tmdbId a 'peliculas'
    ratings.csv         → colección 'ml_ratings'      (33 millones de filas)
    tags.csv            → colección 'ml_tags'
    genome-tags.csv     → colección 'ml_genome_tags'
    genome-scores.csv   → colección 'ml_genome_scores' (el más grande)
"""
import argparse
import csv
from datetime import datetime, timezone
from pathlib import Path
import pymongo

cliente = pymongo.MongoClient("mongodb://localhost:27017")
db      = cliente["cinerec"]

BLOQUE = 10_000  # filas que insertamos de golpe en cada llamada a insert_many


def leer_csv(ruta: Path):
    """Generador: devuelve una fila a la vez para no cargar todo en memoria."""
    with open(ruta, encoding="utf-8") as f:
        for fila in csv.DictReader(f):
            yield fila


def insertar_en_bloques(coleccion, generador_docs):
    """Acumula docs en un bloque y los inserta de golpe cada BLOQUE filas."""
    bloque = []
    total  = 0
    for doc in generador_docs:
        bloque.append(doc)
        if len(bloque) >= BLOQUE:
            try:
                coleccion.insert_many(bloque, ordered=False)
            except pymongo.errors.BulkWriteError as e:
                total += e.details["nInserted"]
                bloque = []
                continue
            total += len(bloque)
            bloque = []
    # último bloque que quedó incompleto
    if bloque:
        try:
            coleccion.insert_many(bloque, ordered=False)
            total += len(bloque)
        except pymongo.errors.BulkWriteError as e:
            total += e.details["nInserted"]
    return total


def importar_peliculas(carpeta: Path):
    """movies.csv → colección 'peliculas'"""
    def generar():
        for fila in leer_csv(carpeta / "movies.csv"):
            genres = fila["genres"]
            yield {
                "_id":    int(fila["movieId"]),
                "title":  fila["title"],
                "genres": [] if genres == "(no genres listed)" else genres.split("|"),
            }

    total = insertar_en_bloques(db["peliculas"], generar())
    print(f"  películas:      {total:>10,}")


def importar_links(carpeta: Path):
    """links.csv → añade imdbId y tmdbId a cada película"""
    ops = []
    for fila in leer_csv(carpeta / "links.csv"):
        ops.append(pymongo.UpdateOne(
            {"_id": int(fila["movieId"])},
            {"$set": {
                "imdb_id": fila["imdbId"],
                "tmdb_id": int(fila["tmdbId"]) if fila["tmdbId"] else None,
            }}
        ))
        if len(ops) >= BLOQUE:
            db["peliculas"].bulk_write(ops, ordered=False)
            ops = []
    if ops:
        db["peliculas"].bulk_write(ops, ordered=False)
    print(f"  links:          OK")


def importar_ratings(carpeta: Path):
    """ratings.csv → colección 'ml_ratings' (33 millones de filas, tarda unos minutos)"""
    def generar():
        for fila in leer_csv(carpeta / "ratings.csv"):
            yield {
                "user_id":  int(fila["userId"]),
                "movie_id": int(fila["movieId"]),
                "rating":   float(fila["rating"]),
                "fecha":    datetime.fromtimestamp(int(fila["timestamp"]), tz=timezone.utc),
            }

    total = insertar_en_bloques(db["ml_ratings"], generar())
    print(f"  ratings:        {total:>10,}")


def importar_tags(carpeta: Path):
    """tags.csv → colección 'ml_tags'"""
    def generar():
        for fila in leer_csv(carpeta / "tags.csv"):
            yield {
                "user_id":  int(fila["userId"]),
                "movie_id": int(fila["movieId"]),
                "tag":      fila["tag"],
                "fecha":    datetime.fromtimestamp(int(fila["timestamp"]), tz=timezone.utc),
            }

    total = insertar_en_bloques(db["ml_tags"], generar())
    print(f"  tags:           {total:>10,}")


def importar_genome_tags(carpeta: Path):
    """genome-tags.csv → colección 'ml_genome_tags' (lista de etiquetas con su id)"""
    def generar():
        for fila in leer_csv(carpeta / "genome-tags.csv"):
            yield {
                "_id": int(fila["tagId"]),  # tagId como _id para búsquedas rápidas
                "tag": fila["tag"],
            }

    total = insertar_en_bloques(db["ml_genome_tags"], generar())
    print(f"  genome-tags:    {total:>10,}")


def importar_genome_scores(carpeta: Path):
    """
    genome-scores.csv → colección 'ml_genome_scores'
    Relevancia de cada tag para cada película (número entre 0 y 1).
    Es el fichero más grande, puede tardar varios minutos.
    """
    def generar():
        for fila in leer_csv(carpeta / "genome-scores.csv"):
            yield {
                "movie_id":  int(fila["movieId"]),
                "tag_id":    int(fila["tagId"]),
                "relevance": float(fila["relevance"]),
            }

    total = insertar_en_bloques(db["ml_genome_scores"], generar())
    print(f"  genome-scores:  {total:>10,}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--carpeta", required=True, help="Ruta a la carpeta ml-latest")
    args = parser.parse_args()

    carpeta = Path(args.carpeta)
    if not carpeta.exists():
        print(f"Error: no existe la carpeta {carpeta}")
        raise SystemExit(1)

    print("Importando MovieLens (ml-latest)...")
    print("Colección               Filas")
    print("-" * 35)
    importar_peliculas(carpeta)
    importar_links(carpeta)
    importar_ratings(carpeta)       # el más lento, ~33M filas
    importar_tags(carpeta)
    importar_genome_tags(carpeta)
    importar_genome_scores(carpeta) # el más grande
    print("-" * 35)
    print("Importación completada")
    cliente.close()
