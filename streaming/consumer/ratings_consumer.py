from kafka import KafkaConsumer
from kafka.errors import KafkaError, NoBrokersAvailable

from pymongo import MongoClient
from pymongo.errors import PyMongoError

import json
from pathlib import Path

import sys
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
from config import KAFKA_TOPIC, KAFKA_SERVER, MONGO_URI, DATABASE_NAME


# =========================
# CREATE CONSUMER
# =========================

def create_consumer():
    try:
        consumer = KafkaConsumer(
            KAFKA_TOPIC,
            bootstrap_servers=KAFKA_SERVER,
            auto_offset_reset="earliest",
            enable_auto_commit=True,
            group_id="movie-group",
            value_deserializer=lambda x: json.loads(
                x.decode("utf-8")
            )
        )
        print("Connected to Kafka successfully.")
        return consumer

    except NoBrokersAvailable:
        print(f"Error: Could not connect to Kafka at {KAFKA_SERVER}.")
        print("Make sure Kafka is running (docker compose up).")
        sys.exit(1)


# =========================
# CONNECT TO MONGODB
# =========================

def create_mongo_collection():
    try:
        mongo_client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        mongo_client.server_info()  # Force connection check
        collection = mongo_client[DATABASE_NAME]["ratings_realtime"]
        print("Connected to MongoDB successfully.")
        return collection

    except PyMongoError as e:
        print(f"Error: Could not connect to MongoDB — {e}")
        print("Make sure MongoDB is running (docker compose up).")
        sys.exit(1)


# =========================
# CONSUME EVENTS
# =========================

def consume_events(consumer, collection):

    print("\nWaiting for Kafka events...\n")

    for message in consumer:

        event = message.value

        print(f"Received: {event}")

        try:
            collection.insert_one(event)

        except PyMongoError as e:
            print(f"Warning: Failed to save event to MongoDB — {e}")


# =========================
# MAIN
# =========================

if __name__ == "__main__":

    consumer = create_consumer()
    collection = create_mongo_collection()

    try:
        consume_events(consumer, collection)

    except KafkaError as e:
        print(f"Error: Kafka connection lost — {e}")
        sys.exit(1)

    except KeyboardInterrupt:
        print("\nConsumer stopped manually.")