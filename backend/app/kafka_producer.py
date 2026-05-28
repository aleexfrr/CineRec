import asyncio
import json
import os
import logging
from datetime import datetime, timezone
from functools import partial

logger = logging.getLogger(__name__)

KAFKA_SERVER = os.getenv("KAFKA_SERVER", "localhost:9092")
KAFKA_TOPIC  = os.getenv("KAFKA_TOPIC",  "movie_ratings")

_producer = None


def _get_producer():
    global _producer
    if _producer is not None:
        return _producer
    try:
        from kafka import KafkaProducer
        _producer = KafkaProducer(
            bootstrap_servers=KAFKA_SERVER,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            request_timeout_ms=5000,
            max_block_ms=3000,
        )
        logger.info("Kafka producer connected to %s", KAFKA_SERVER)
    except Exception as e:
        logger.warning("Kafka producer not available: %s", e)
    return _producer


def _send_sync(event: dict):
    producer = _get_producer()
    if producer is None:
        return
    try:
        producer.send(KAFKA_TOPIC, value=event)
        producer.flush(timeout=2)
    except Exception as e:
        logger.warning("Kafka send failed: %s", e)


async def publish_rating(username: str, movie_id: int, rating: float):
    event = {
        "userId":    username,
        "movieId":   movie_id,
        "rating":    rating,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, partial(_send_sync, event))
