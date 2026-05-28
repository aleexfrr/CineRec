import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

# MongoDB — usado por ETL, recomendadores y streaming
MONGO_URI     = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DATABASE_NAME = os.getenv("DATABASE_NAME", "movie_recommender")

# Kafka — usado por los módulos de streaming
KAFKA_TOPIC  = os.getenv("KAFKA_TOPIC", "movie_ratings")
KAFKA_SERVER = os.getenv("KAFKA_SERVER", "localhost:9092")
