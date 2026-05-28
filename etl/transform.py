import sys
import pandas as pd
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from extract import load_all_datasets


BASE_DIR = Path(__file__).resolve().parent.parent
PROCESSED_DATA_PATH = BASE_DIR / "data" / "processed"


# =========================
# MOVIES TRANSFORMATIONS
# =========================

def transform_movies(movies_df):
    """
    Clean and transform movies dataset
    """

    movies = movies_df.copy()

    # Remove null values
    movies.dropna(inplace=True)

    # Extract year from title
    movies["year"] = movies["title"].str.extract(r"\((\d{4})\)")

    # Remove year from title
    movies["title"] = (
        movies["title"]
        .str.replace(r"\(\d{4}\)", "", regex=True)
        .str.strip()
    )

    # Convert genres into list
    movies["genres"] = movies["genres"].apply(
        lambda x: x.split("|")
    )

    return movies


# =========================
# RATINGS TRANSFORMATIONS
# =========================

def transform_ratings(ratings_df):
    """
    Clean and transform ratings dataset
    """

    ratings = ratings_df.copy()

    # Remove null values
    ratings.dropna(inplace=True)

    # Convert timestamp to datetime
    ratings["timestamp"] = pd.to_datetime(
        ratings["timestamp"],
        unit="s"
    )

    return ratings


# =========================
# USERS TRANSFORMATIONS
# =========================

def transform_users(users_df):
    """
    Clean and transform users dataset
    """

    users = users_df.copy()

    # Remove null values
    users.dropna(inplace=True)

    # Convert gender to readable values
    users["gender"] = users["gender"].replace({
        "M": "Male",
        "F": "Female"
    })

    return users


# =========================
# SAVE CLEAN DATASETS
# =========================

def save_processed_data(movies, ratings, users):
    """
    Save processed datasets into processed folder
    """

    PROCESSED_DATA_PATH.mkdir(parents=True, exist_ok=True)

    movies.to_csv(
        PROCESSED_DATA_PATH / "movies_clean.csv",
        index=False
    )

    ratings.to_csv(
        PROCESSED_DATA_PATH / "ratings_clean.csv",
        index=False
    )

    users.to_csv(
        PROCESSED_DATA_PATH / "users_clean.csv",
        index=False
    )

    print("\nProcessed datasets saved successfully.")


# =========================
# MAIN PIPELINE
# =========================

def main():

    print("\nLoading datasets...")
    movies_df, ratings_df, users_df = load_all_datasets()

    print("Transforming movies...")
    movies_clean = transform_movies(movies_df)

    print("Transforming ratings...")
    ratings_clean = transform_ratings(ratings_df)

    print("Transforming users...")
    users_clean = transform_users(users_df)

    print("Saving processed datasets...")
    save_processed_data(
        movies_clean,
        ratings_clean,
        users_clean
    )

    print("\nETL Transformation completed successfully.")


if __name__ == "__main__":
    main()