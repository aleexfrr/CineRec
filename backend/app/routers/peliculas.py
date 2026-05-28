import asyncio
import re
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Query
from typing import Optional

from app.auth_utils import usuario_actual
from app.database import db, db_ml
from app.kafka_producer import publish_rating
from app.ml_sync import sync_rating

router = APIRouter(tags=["peliculas"])

GRUPOS_GENEROS = {
    "action_adventure":    ["Action", "Adventure"],
    "drama_romance":       ["Drama", "Romance"],
    "horror_thriller":     ["Horror", "Thriller"],
    "comedy_animation":    ["Comedy", "Animation"],
    "scifi_fantasy":       ["Sci-Fi", "Fantasy"],
    "documentary_history": ["Documentary"],
}


def _formato(doc: dict) -> dict:
    titulo = doc.get("title", "")
    match = re.search(r"\((\d{4})\)", titulo)
    anio  = int(match.group(1)) if match else None
    titulo_limpio = re.sub(r"\s*\(\d{4}\)$", "", titulo).strip()

    return {
        "id":           doc["_id"],
        "title":        titulo_limpio,
        "year":         anio,
        "genre":        " / ".join(doc.get("genres", [])),
        "genres":       doc.get("genres", []),
        "rating":       round(doc.get("rating_avg", 0), 1),
        "rating_count": doc.get("rating_count", 0),
        "poster_url":   doc.get("poster_url"),
        "description":  None,
        "duration":     None,
        "imdb_id":      doc.get("imdb_id"),
        "tmdb_id":      doc.get("tmdb_id"),
    }


# ── BUSCAR ────────────────────────────────────────────────────────────────────
@router.get("/movies/search")
async def buscar(
    q:          Optional[str]   = Query(None),
    genre:      Optional[str]   = Query(None),
    year:       Optional[int]   = Query(None),
    min_rating: Optional[float] = Query(None),
    limit:      int             = Query(20, ge=1, le=100),
    _user: dict = Depends(usuario_actual),
):
    filtro: dict = {"rating_count": {"$gte": 10}}
    if q:
        filtro["$text"] = {"$search": q}
    if genre:
        filtro["genres"] = genre
    if year:
        filtro["title"] = {"$regex": rf"\({year}\)"}
    if min_rating:
        filtro["rating_avg"] = {"$gte": min_rating}

    sort = [("rating_avg", -1)] if not q else [("rating_count", -1)]
    docs = await db["peliculas"].find(filtro).sort(sort).limit(limit).to_list(length=limit)
    return {"movies": [_formato(d) for d in docs]}


# ── TENDENCIAS ────────────────────────────────────────────────────────────────
@router.get("/movies/trending")
async def tendencias(_user: dict = Depends(usuario_actual)):
    docs = await db["peliculas"].find(
        {"rating_count": {"$gte": 200}, "rating_avg": {"$gte": 3.5}}
    ).sort([("rating_count", -1)]).limit(20).to_list(length=20)
    return {"movies": [_formato(d) for d in docs]}


# ── RECOMENDACIONES PERSONALIZADAS ────────────────────────────────────────────
@router.get("/movies/recommendations")
async def recomendaciones(user: dict = Depends(usuario_actual)):
    user_id = str(user["_id"])

    # 1. Obtener todas las valoraciones del usuario
    valoraciones = await db["valoraciones"].find(
        {"user_id": user_id}
    ).to_list(length=500)

    rated_ids = [v["movie_id"] for v in valoraciones]

    # Sin valoraciones → usar preferencias del onboarding o trending
    if not valoraciones:
        return await _recomendaciones_por_preferencias(user, rated_ids=[])

    # 2. Construir perfil de géneros ponderado por puntuación
    #    Películas con ≥3 estrellas pesan positivo; <3 pesan negativo (no recomendar)
    liked_ids = [v["movie_id"] for v in valoraciones if v["rating"] >= 3.0]

    if not liked_ids:
        return await tendencias(user)

    # Obtener géneros de las películas valoradas positivamente
    peliculas_vistas = await db["peliculas"].find(
        {"_id": {"$in": liked_ids}},
        {"genres": 1, "_id": 1}
    ).to_list(length=len(liked_ids))

    # Mapa movie_id → rating
    rating_por_id = {v["movie_id"]: v["rating"] for v in valoraciones}

    # Peso de cada género = suma de ratings de películas que lo contienen
    genre_weight: dict[str, float] = {}
    for peli in peliculas_vistas:
        peso = rating_por_id.get(peli["_id"], 3.0)
        for g in peli.get("genres", []):
            genre_weight[g] = genre_weight.get(g, 0.0) + peso

    # Top 5 géneros preferidos
    top_genres = sorted(genre_weight, key=lambda g: -genre_weight[g])[:5]

    # 3. Candidatos: películas no vistas con esos géneros y buena calidad
    candidatos = await db["peliculas"].find({
        "genres":       {"$in": top_genres},
        "_id":          {"$nin": rated_ids},
        "rating_count": {"$gte": 30},
        "rating_avg":   {"$gte": 3.0},
    }, {"_id": 1, "title": 1, "genres": 1, "rating_avg": 1,
        "rating_count": 1, "poster_url": 1, "imdb_id": 1, "tmdb_id": 1}
    ).to_list(length=200)

    if not candidatos:
        # Fallback: cualquier película no vista con buen rating
        candidatos = await db["peliculas"].find({
            "_id":          {"$nin": rated_ids},
            "rating_count": {"$gte": 100},
            "rating_avg":   {"$gte": 3.5},
        }).sort([("rating_avg", -1)]).limit(20).to_list(length=20)
        return {"movies": [_formato(d) for d in candidatos], "source": "trending"}

    # 4. Puntuar candidatos: afinidad de género × rating medio del dataset
    def puntuar(doc):
        afinidad = sum(genre_weight.get(g, 0) for g in doc.get("genres", []))
        return afinidad * doc.get("rating_avg", 3.0)

    candidatos.sort(key=puntuar, reverse=True)
    top20 = candidatos[:20]

    return {
        "movies":      [_formato(d) for d in top20],
        "source":      "content_based",
        "top_genres":  top_genres,
    }


@router.post("/movies/recommendations/refresh")
async def refresh_recomendaciones(user: dict = Depends(usuario_actual)):
    """
    Fuerza la regeneración de recomendaciones para el usuario actual.
    Llama al mismo algoritmo que GET /movies/recommendations y devuelve el resultado.
    El frontend puede llamar a este endpoint al abrir la pestaña de recomendaciones
    o después de que el usuario valore nuevas películas.
    """
    return await recomendaciones(user)


async def _recomendaciones_por_preferencias(user: dict, rated_ids: list) -> dict:
    """Fallback cuando el usuario no tiene valoraciones: usa preferred_groups del onboarding."""
    preferred = user.get("preferred_groups", {})
    generos = []
    for grupo, puntos in preferred.items():
        if puntos > 0 and grupo in GRUPOS_GENEROS:
            generos.extend(GRUPOS_GENEROS[grupo] * puntos)

    if not generos:
        docs = await db["peliculas"].find(
            {"rating_count": {"$gte": 200}, "rating_avg": {"$gte": 3.5}}
        ).sort([("rating_count", -1)]).limit(20).to_list(length=20)
        return {"movies": [_formato(d) for d in docs], "source": "trending"}

    docs = await db["peliculas"].find({
        "genres":       {"$in": generos},
        "_id":          {"$nin": rated_ids},
        "rating_count": {"$gte": 50},
        "rating_avg":   {"$gte": 3.8},
    }).sort([("rating_avg", -1)]).limit(20).to_list(length=20)

    return {"movies": [_formato(d) for d in docs], "source": "onboarding"}


# ── WATCHLIST (GET antes de {movie_id} para evitar conflictos de ruta) ────────
@router.get("/movies/watchlist")
async def mi_watchlist(user: dict = Depends(usuario_actual)):
    ids = user.get("watchlist", [])
    if not ids:
        return {"movies": []}
    docs = await db["peliculas"].find({"_id": {"$in": ids}}).to_list(length=len(ids))
    return {"movies": [_formato(d) for d in docs]}


# ── MIS VALORACIONES ──────────────────────────────────────────────────────────
@router.get("/movies/my-ratings")
async def mis_valoraciones(user: dict = Depends(usuario_actual)):
    vals = await db["valoraciones"].find(
        {"user_id": str(user["_id"])}
    ).sort("timestamp", -1).to_list(length=500)

    if not vals:
        return {"ratings": []}

    ids  = [v["movie_id"] for v in vals]
    docs = {d["_id"]: d async for d in db["peliculas"].find({"_id": {"$in": ids}})}

    result = []
    for v in vals:
        doc = docs.get(v["movie_id"])
        if doc:
            f = _formato(doc)
            f["user_rating"] = v["rating"]
            result.append(f)

    return {"ratings": result}


# ── POR GÉNERO ────────────────────────────────────────────────────────────────
@router.get("/movies/genre/{genre}")
async def por_genero(
    genre: str,
    limit: int = Query(20, ge=1, le=50),
    _user: dict = Depends(usuario_actual),
):
    docs = await db["peliculas"].find(
        {"genres": genre, "rating_count": {"$gte": 30}, "rating_avg": {"$gte": 3.2}}
    ).sort([("rating_avg", -1)]).limit(limit).to_list(length=limit)
    return {"movies": [_formato(d) for d in docs]}


# ── VALORAR ───────────────────────────────────────────────────────────────────
@router.post("/movies/{movie_id}/rate")
async def valorar(movie_id: int, body: dict, user: dict = Depends(usuario_actual)):
    puntuacion = float(body.get("score", body.get("rating", 0)))
    user_id    = str(user["_id"])

    await db["valoraciones"].update_one(
        {"user_id": user_id, "movie_id": movie_id},
        {"$set": {"rating": puntuacion, "timestamp": datetime.now(timezone.utc)}},
        upsert=True,
    )
    asyncio.create_task(publish_rating(user["nombre"], movie_id, puntuacion))

    # Sincronizar con dataset ML (movie_recommender.ratings)
    ml_user_id = user.get("ml_user_id")
    if ml_user_id:
        asyncio.create_task(sync_rating(ml_user_id, movie_id, puntuacion, db_ml))

    return {"ok": True}


# ── WATCHLIST ADD / REMOVE ────────────────────────────────────────────────────
@router.post("/movies/{movie_id}/watchlist")
async def watchlist_add(movie_id: int, user: dict = Depends(usuario_actual)):
    await db["usuarios"].update_one(
        {"_id": user["_id"]},
        {"$addToSet": {"watchlist": movie_id}},
    )
    return {"ok": True}

@router.delete("/movies/{movie_id}/watchlist")
async def watchlist_remove(movie_id: int, user: dict = Depends(usuario_actual)):
    await db["usuarios"].update_one(
        {"_id": user["_id"]},
        {"$pull": {"watchlist": movie_id}},
    )
    return {"ok": True}
