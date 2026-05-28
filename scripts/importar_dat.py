"""
Importa MovieLens 1M (.dat) a la colección 'peliculas' de MongoDB (cinerec).
Calcula rating_avg y rating_count desde ratings.dat.

Uso:
    python3 scripts/importar_dat.py
"""
from pathlib import Path
from collections import defaultdict
import pymongo

BASE_DIR  = Path(__file__).resolve().parent.parent
DATA_DIR  = BASE_DIR / "data" / "raw"
MONGO_URL = "mongodb://localhost:27017"
DB_NAME   = "cinerec"

client = pymongo.MongoClient(MONGO_URL)
col    = client[DB_NAME]["peliculas"]


def leer_peliculas():
    peliculas = {}
    with open(DATA_DIR / "movies.dat", encoding="latin-1") as f:
        for linea in f:
            partes = linea.strip().split("::")
            if len(partes) < 3:
                continue
            movie_id = int(partes[0])
            titulo   = partes[1]
            generos  = [g.strip() for g in partes[2].split("|") if g.strip() and g != "(no genres listed)"]
            # normalizar "Children's" → "Children"
            generos  = [g.replace("Children's", "Children").replace("Film-Noir", "Film-Noir") for g in generos]
            peliculas[movie_id] = {"title": titulo, "genres": generos}
    return peliculas


def calcular_ratings():
    stats = defaultdict(lambda: {"suma": 0.0, "count": 0})
    with open(DATA_DIR / "ratings.dat", encoding="latin-1") as f:
        for linea in f:
            partes = linea.strip().split("::")
            if len(partes) < 3:
                continue
            movie_id = int(partes[1])
            rating   = float(partes[2])
            stats[movie_id]["suma"]  += rating
            stats[movie_id]["count"] += 1
    return stats


def main():
    print("Leyendo películas...")
    peliculas = leer_peliculas()
    print(f"  {len(peliculas)} películas")

    print("Calculando ratings...")
    stats = calcular_ratings()
    print(f"  {len(stats)} películas con ratings")

    print("Insertando en MongoDB (cinerec.peliculas)...")
    col.drop()

    docs = []
    for movie_id, p in peliculas.items():
        s = stats.get(movie_id, {"suma": 0.0, "count": 0})
        avg = round(s["suma"] / s["count"], 2) if s["count"] > 0 else 0.0
        docs.append({
            "_id":          movie_id,
            "title":        p["title"],
            "genres":       p["genres"],
            "rating_avg":   avg,
            "rating_count": s["count"],
            "poster_url":   None,
            "imdb_id":      None,
            "tmdb_id":      None,
        })

    col.insert_many(docs, ordered=False)

    # Índices necesarios para las búsquedas del backend
    col.create_index([("title", pymongo.TEXT)])
    col.create_index("genres")
    col.create_index("rating_count")
    col.create_index("rating_avg")

    total = col.count_documents({})
    con_ratings = col.count_documents({"rating_count": {"$gte": 1}})
    print(f"\nImportadas {total} películas ({con_ratings} con al menos 1 rating)")
    print("Listo.")
    client.close()


if __name__ == "__main__":
    main()
