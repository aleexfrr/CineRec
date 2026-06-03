import asyncio
import logging

logger = logging.getLogger(__name__)


async def recomendar_ml(ml_user_id: int, top_n: int = 20) -> tuple[list[int], str]:
    """
    Intenta modelos ML en orden: SVD colaborativo → TF-IDF basado en contenido.
    Devuelve (lista de movieIds, nombre de la fuente) o ([], "") si ninguno está entrenado.
    """
    for _fn, source in [
        (_collab, "collaborative"),
        (_content, "content_based_ml"),
    ]:
        try:
            ids = await asyncio.to_thread(_fn, ml_user_id, top_n)
            if ids:
                return ids, source
        except FileNotFoundError:
            logger.info("Modelo '%s' no entrenado aún, saltando.", source)
        except Exception as exc:
            logger.warning("Fallo en recomendador '%s': %s", source, exc)

    return [], ""


def _collab(user_id: int, top_n: int) -> list[int]:
    from recommender.collaborative.collaborative_filtering import predict
    return [r["movieId"] for r in predict(user_id, top_n)]


def _content(user_id: int, top_n: int) -> list[int]:
    from recommender.content_based.content_based import predict
    return [r["movieId"] for r in predict(user_id, top_n)]
