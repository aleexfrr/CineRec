from kafka import KafkaProducer
from kafka.errors import KafkaError, NoBrokersAvailable

import pandas as pd
import json
import time
from pathlib import Path

import sys
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
from config import KAFKA_TOPIC, KAFKA_SERVER


BASE_DIR = Path(__file__).resolve().parent.parent.parent
RATINGS_PATH = BASE_DIR / "data" / "processed" / "ratings_clean.csv"


# =========================
# CREATE PRODUCER
# =========================

def create_producer():
    try:
        producer = KafkaProducer(
            bootstrap_servers=KAFKA_SERVER,
            value_serializer=lambda v: json.dumps(v).encode("utf-8")
        )
        print("Connected to Kafka successfully.")
        return producer

    except NoBrokersAvailable:
        print(f"Error: Could not connect to Kafka at {KAFKA_SERVER}.")
        print("Make sure Kafka is running (docker compose up).")
        sys.exit(1)


# =========================
# LOAD RATINGS
# =========================

def load_ratings():
    if not RATINGS_PATH.exists():
        print(f"Error: Ratings file not found at {RATINGS_PATH}.")
        print("Run the ETL pipeline first.")
        sys.exit(1)

    return pd.read_csv(RATINGS_PATH)


# =========================
# STREAM EVENTS
# =========================

def stream_ratings(producer, ratings):

    sent = 0
    failed = 0

    print("\nStreaming ratings to Kafka...\n")

    for _, row in ratings.iterrows():

        event = {
            "userId": int(row["userId"]),
            "movieId": int(row["movieId"]),
            "rating": float(row["rating"]),
            "timestamp": str(row["timestamp"])
        }

        try:
            producer.send(KAFKA_TOPIC, value=event)
            print(f"Sent: {event}")
            sent += 1

        except KafkaError as e:
            print(f"Warning: Failed to send event {event} — {e}")
            failed += 1

        # Simulate realtime streaming
        time.sleep(1)

    producer.flush()

    print(f"\nStreaming completed. Sent: {sent} | Failed: {failed}")


# =========================
# MAIN
# =========================

if __name__ == "__main__":

    producer = create_producer()
    ratings = load_ratings()
    stream_ratings(producer, ratings)