from pymongo import MongoClient
import pandas as pd
from pathlib import Path

import sys
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
from config import MONGO_URI, DATABASE_NAME


_client = None

def get_db():
    global _client
    if _client is None:
        _client = MongoClient(MONGO_URI)
    return _client[DATABASE_NAME]


# =========================
# GET RATINGS DATA
# =========================

def load_ratings_dataframe():
    """
    Load ratings collection into pandas dataframe
    """

    ratings_cursor = get_db()["ratings"].find()

    ratings_df = pd.DataFrame(list(ratings_cursor))

    return ratings_df


def load_movies_dataframe():
    """
    Load movies collection into pandas dataframe
    """

    movies_cursor = get_db()["movies"].find()

    movies_df = pd.DataFrame(list(movies_cursor))

    return movies_df


# =========================
# POPULARITY RECOMMENDER
# =========================

def generate_popular_movies(
    min_votes=100,
    top_n=10
):
    """
    Generate top popular movies based on:
    - average rating
    - minimum number of votes
    """

    print("\nLoading datasets from MongoDB...")

    ratings_df = load_ratings_dataframe()
    movies_df = load_movies_dataframe()

    print("Datasets loaded successfully.")

    # =========================
    # AGGREGATE RATINGS
    # =========================

    print("\nCalculating movie statistics...")

    movie_stats = (
        ratings_df
        .groupby("movieId")
        .agg(
            average_rating=("rating", "mean"),
            rating_count=("rating", "count")
        )
        .reset_index()
    )

    # Filter by minimum votes
    movie_stats = movie_stats[
        movie_stats["rating_count"] >= min_votes
    ]

    # Sort by average rating
    movie_stats = movie_stats.sort_values(
        by="average_rating",
        ascending=False
    )

    # Keep top N movies
    top_movies = movie_stats.head(top_n)

    # =========================
    # MERGE WITH MOVIES
    # =========================

    recommendations = top_movies.merge(
        movies_df,
        on="movieId"
    )

    recommendations = recommendations[
        [
            "movieId",
            "title",
            "genres",
            "average_rating",
            "rating_count"
        ]
    ]

    return recommendations


# =========================
# SAVE RECOMMENDATIONS
# =========================

def save_recommendations(recommendations_df):
    """
    Save recommendations into MongoDB
    """

    print("\nSaving recommendations into MongoDB...")

    recommendations_collection = get_db()["recommendations"]

    # Remove previous recommendations
    recommendations_collection.delete_many({
        "type": "popularity"
    })

    recommendations_data = recommendations_df.to_dict("records")

    documents = []

    for recommendation in recommendations_data:

        documents.append({
            "type": "popularity",
            "movieId": recommendation["movieId"],
            "title": recommendation["title"],
            "genres": recommendation["genres"],
            "average_rating": round(
                recommendation["average_rating"],
                2
            ),
            "rating_count": int(
                recommendation["rating_count"]
            )
        })

    recommendations_collection.insert_many(documents)

    print(f"{len(documents)} recommendations saved.")


# =========================
# DISPLAY RESULTS
# =========================

def display_recommendations(recommendations_df):

    print("\n==============================")
    print(" TOP POPULAR MOVIES ")
    print("==============================\n")

    for i, (_, row) in enumerate(recommendations_df.iterrows(), start=1):

        print(
            f"{i}. "
            f"{row['title']} | "
            f"⭐ {row['average_rating']:.2f} | "
            f"Votes: {row['rating_count']}"
        )

    print("\n==============================\n")


# =========================
# MAIN
# =========================

def main():

    recommendations = generate_popular_movies(
        min_votes=100,
        top_n=10
    )

    display_recommendations(recommendations)

    save_recommendations(recommendations)

    print("Popularity recommender completed successfully.")


if __name__ == "__main__":
    main()