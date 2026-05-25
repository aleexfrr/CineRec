import pandas as pd
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DATA_PATH = BASE_DIR / "data" / "raw"


def load_movies():
    """
    Load movies dataset
    """
    movies = pd.read_csv(
        RAW_DATA_PATH / "movies.dat",
        sep="::",
        engine="python",
        encoding="latin-1",
        names=["movieId", "title", "genres"]
    )

    return movies


def load_ratings():
    """
    Load ratings dataset
    """
    ratings = pd.read_csv(
        RAW_DATA_PATH / "ratings.dat",
        sep="::",
        engine="python",
        names=["userId", "movieId", "rating", "timestamp"]
    )

    return ratings


def load_users():
    """
    Load users dataset
    """
    users = pd.read_csv(
        RAW_DATA_PATH / "users.dat",
        sep="::",
        engine="python",
        names=["userId", "gender", "age", "occupation", "zipCode"]
    )

    return users


def load_all_datasets():
    """
    Load all MovieLens datasets
    """
    movies = load_movies()
    ratings = load_ratings()
    users = load_users()

    return movies, ratings, users


if __name__ == "__main__":

    movies_df, ratings_df, users_df = load_all_datasets()

    print("\n=== MOVIES ===")
    print(movies_df.head())

    print("\n=== RATINGS ===")
    print(ratings_df.head())

    print("\n=== USERS ===")
    print(users_df.head())