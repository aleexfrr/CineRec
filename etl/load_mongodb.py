from pathlib import Path

import pandas as pd
from pymongo import MongoClient

import sys
sys.path.append(str(Path(__file__).resolve().parent.parent))
from config import MONGO_URI, DATABASE_NAME


# =========================
# PATHS
# =========================

BASE_DIR = Path(__file__).resolve().parent.parent
PROCESSED_DATA_PATH = BASE_DIR / "data" / "processed"


# =========================
# CONNECT TO MONGODB
# =========================

_client = None

def get_db():
    global _client
    if _client is None:
        _client = MongoClient(MONGO_URI)
    return _client[DATABASE_NAME]


# =========================
# LOAD CLEAN DATASETS
# =========================

def load_processed_datasets():

    movies = pd.read_csv(
        PROCESSED_DATA_PATH / "movies_clean.csv"
    )

    ratings = pd.read_csv(
        PROCESSED_DATA_PATH / "ratings_clean.csv"
    )

    users = pd.read_csv(
        PROCESSED_DATA_PATH / "users_clean.csv"
    )

    return movies, ratings, users


# =========================
# INSERT MOVIES
# =========================

def insert_movies(movies_df):

    movies_collection = get_db()["movies"]

    # Remove old data
    movies_collection.delete_many({})

    # Convert dataframe to dictionary
    movies_data = movies_df.to_dict("records")

    # Insert documents
    movies_collection.insert_many(movies_data)

    print(f"Inserted {len(movies_data)} movies")


# =========================
# INSERT RATINGS
# =========================

def insert_ratings(ratings_df):

    ratings_collection = get_db()["ratings"]

    # Remove old data
    ratings_collection.delete_many({})

    # Convert dataframe to dictionary
    ratings_data = ratings_df.to_dict("records")

    # Insert documents
    ratings_collection.insert_many(ratings_data)

    print(f"Inserted {len(ratings_data)} ratings")


# =========================
# INSERT USERS
# =========================

def insert_users(users_df):

    users_collection = get_db()["users"]

    # Remove old data
    users_collection.delete_many({})

    # Convert dataframe to dictionary
    users_data = users_df.to_dict("records")

    # Insert documents
    users_collection.insert_many(users_data)

    print(f"Inserted {len(users_data)} users")


# =========================
# CREATE INDEXES
# =========================

def create_indexes():

    print("\nCreating indexes...")

    db = get_db()
    db.movies.create_index("movieId")

    db.ratings.create_index("userId")
    db.ratings.create_index("movieId")

    db.users.create_index("userId")

    print("Indexes created successfully")


# =========================
# MAIN PIPELINE
# =========================

def main():

    print("\nLoading processed datasets...")

    movies_df, ratings_df, users_df = load_processed_datasets()

    print("\nLoading data into MongoDB...")

    insert_movies(movies_df)

    insert_ratings(ratings_df)

    insert_users(users_df)

    create_indexes()

    print("\nMongoDB load completed successfully")


if __name__ == "__main__":
    main()