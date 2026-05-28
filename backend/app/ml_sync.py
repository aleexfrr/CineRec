import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

_GENDER_MAP = {
    "hombre": "M", "male": "M", "masculino": "M", "m": "M",
    "mujer": "F",  "female": "F", "femenino": "F",  "f": "F",
}


async def sync_new_user(user_doc: dict, db_ml) -> int | None:
    """
    Inserta el usuario web en movie_recommender.users con un userId entero.
    Devuelve el ml_user_id asignado, o None si falla.
    """
    try:
        last = await db_ml["users"].find_one(sort=[("userId", -1)], projection={"userId": 1})
        next_id = (last["userId"] + 1) if last else 6041

        gender_raw = (user_doc.get("genero") or "").strip().lower()
        gender = _GENDER_MAP.get(gender_raw, "F")

        await db_ml["users"].insert_one({
            "userId":     next_id,
            "gender":     gender,
            "age":        user_doc.get("edad") or 25,
            "occupation": 0,
            "zipCode":    "00000",
            "nombre":     user_doc.get("nombre", ""),
            "web_id":     str(user_doc.get("_id", "")),
        })
        logger.info("ML sync: nuevo usuario userId=%d", next_id)
        return next_id
    except Exception as e:
        logger.warning("ML sync_new_user falló: %s", e)
        return None


async def sync_rating(ml_user_id: int, movie_id: int, rating: float, db_ml) -> None:
    """
    Inserta o actualiza la valoración en movie_recommender.ratings.
    """
    try:
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        await db_ml["ratings"].update_one(
            {"userId": ml_user_id, "movieId": movie_id},
            {"$set": {"rating": rating, "timestamp": ts}},
            upsert=True,
        )
        logger.info("ML sync: rating userId=%d movieId=%d rating=%.1f", ml_user_id, movie_id, rating)
    except Exception as e:
        logger.warning("ML sync_rating falló: %s", e)
