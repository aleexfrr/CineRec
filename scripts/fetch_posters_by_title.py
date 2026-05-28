"""
Busca cada película en TMDB por título+año y guarda poster_url + tmdb_id en MongoDB.

Uso:
    python3 scripts/fetch_posters_by_title.py <API_KEY>
"""
import sys
import re
import asyncio
import time
import aiohttp
from pymongo import UpdateOne
import motor.motor_asyncio

MONGO_URL   = "mongodb://localhost:27017"
DB_NAME     = "cinerec"
SEARCH_URL  = "https://api.themoviedb.org/3/search/movie"
POSTER_BASE = "https://image.tmdb.org/t/p/w342"
CONCURRENCY = 20
CHUNK       = 200


def extraer_titulo_anio(titulo_raw: str):
    match = re.search(r"\((\d{4})\)", titulo_raw)
    anio  = match.group(1) if match else None
    titulo = re.sub(r"\s*\(\d{4}\)$", "", titulo_raw).strip()
    # quitar ", The" / ", A" al final y ponerlo al principio
    for art in (", The", ", A", ", An", ", Los", ", Las", ", El", ", La"):
        if titulo.endswith(art):
            titulo = art.strip(", ") + " " + titulo[: -len(art)]
            break
    return titulo, anio


async def buscar_pelicula(session, semaphore, api_key, movie_id, titulo_raw):
    titulo, anio = extraer_titulo_anio(titulo_raw)
    params = {"api_key": api_key, "query": titulo, "language": "es-ES"}
    if anio:
        params["year"] = anio

    async with semaphore:
        for intento in range(3):
            try:
                async with session.get(
                    SEARCH_URL, params=params,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as r:
                    if r.status == 429:
                        await asyncio.sleep(5)
                        continue
                    if r.status == 200:
                        data    = await r.json()
                        results = data.get("results", [])
                        if results:
                            hit  = results[0]
                            path = hit.get("poster_path")
                            return movie_id, hit.get("id"), f"{POSTER_BASE}{path}" if path else None
            except Exception:
                await asyncio.sleep(1)
    return movie_id, None, None


async def main(api_key: str):
    client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URL)
    db     = client[DB_NAME]

    movies = await db["peliculas"].find(
        {"poster_url": None},
        {"_id": 1, "title": 1}
    ).to_list(length=None)

    total = len(movies)
    print(f"Películas sin póster: {total}")
    if total == 0:
        print("¡Todos los pósters ya están descargados!")
        return

    semaphore = asyncio.Semaphore(CONCURRENCY)
    done = found = 0
    t0 = time.time()

    async with aiohttp.ClientSession() as session:
        coros = [
            buscar_pelicula(session, semaphore, api_key, m["_id"], m["title"])
            for m in movies
        ]

        for i in range(0, total, CHUNK):
            batch   = coros[i : i + CHUNK]
            results = await asyncio.gather(*batch)

            bulk = []
            for movie_id, tmdb_id, poster_url in results:
                update = {}
                if poster_url:
                    update["poster_url"] = poster_url
                    found += 1
                if tmdb_id:
                    update["tmdb_id"] = tmdb_id
                if update:
                    bulk.append(UpdateOne({"_id": movie_id}, {"$set": update}))

            if bulk:
                await db["peliculas"].bulk_write(bulk, ordered=False)

            done += len(results)
            elapsed = time.time() - t0
            speed   = done / elapsed if elapsed else 1
            eta     = int((total - done) / speed)
            print(f"  {done}/{total}  con póster: {found}  ({speed:.0f} req/s  ETA {eta}s)")

    print(f"\nListo. {found}/{total} películas con póster ({time.time()-t0:.0f}s)")
    client.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python3 scripts/fetch_posters_by_title.py <TMDB_API_KEY>")
        sys.exit(1)
    asyncio.run(main(sys.argv[1]))
