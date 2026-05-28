"""
Descarga poster_path desde TMDB y guarda poster_url en MongoDB.

Uso:
    python3 scripts/fetch_posters.py <TMDB_API_KEY>

Procesa todas las películas con rating_count >= 10 que tengan tmdb_id.
"""

import sys
import asyncio
import time
import aiohttp
from pymongo import UpdateOne
import motor.motor_asyncio

MONGO_URL   = "mongodb://localhost:27017"
DB_NAME     = "cinerec"
TMDB_BASE   = "https://api.themoviedb.org/3/movie"
POSTER_BASE = "https://image.tmdb.org/t/p/w342"
MIN_RATINGS = 10
CONCURRENCY = 30   # peticiones simultáneas (TMDB permite ~40/s)
CHUNK       = 500  # tamaño del lote para bulk_write


async def fetch_poster(session, semaphore, api_key, movie_id, tmdb_id):
    url = f"{TMDB_BASE}/{tmdb_id}?api_key={api_key}&language=es-ES"
    async with semaphore:
        for attempt in range(2):
            try:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as r:
                    if r.status == 429:
                        await asyncio.sleep(3)
                        continue
                    if r.status == 200:
                        data = await r.json()
                        path = data.get("poster_path")
                        return movie_id, f"{POSTER_BASE}{path}" if path else None
            except Exception:
                pass
    return movie_id, None


async def main(api_key: str):
    client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URL)
    db     = client[DB_NAME]

    movies = await db["peliculas"].find(
        {"rating_count": {"$gte": MIN_RATINGS}, "tmdb_id": {"$exists": True, "$nin": [None, 0]}},
        {"_id": 1, "tmdb_id": 1},
    ).to_list(length=None)

    total = len(movies)
    print(f"Películas a procesar: {total}")

    semaphore = asyncio.Semaphore(CONCURRENCY)
    done = found = 0
    t0 = time.time()

    async with aiohttp.ClientSession() as session:
        coros = [fetch_poster(session, semaphore, api_key, m["_id"], m["tmdb_id"]) for m in movies]

        for i in range(0, total, CHUNK):
            batch   = coros[i:i + CHUNK]
            results = await asyncio.gather(*batch)

            bulk = [UpdateOne({"_id": mid}, {"$set": {"poster_url": url}}) for mid, url in results if url]
            if bulk:
                await db["peliculas"].bulk_write(bulk, ordered=False)
                found += len(bulk)

            done += len(results)
            elapsed = time.time() - t0
            speed   = done / elapsed if elapsed else 1
            eta     = int((total - done) / speed)
            print(f"  {done}/{total}  con póster: {found}  ({speed:.0f} req/s  ETA {eta}s)")

    print(f"\nListo. {found}/{total} películas con póster ({time.time()-t0:.0f}s)")
    client.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python3 scripts/fetch_posters.py <TMDB_API_KEY>")
        sys.exit(1)
    asyncio.run(main(sys.argv[1]))
