from pymongo import MongoClient
import pandas as pd
from pathlib import Path

from surprise import Dataset
from surprise import Reader
from surprise import SVD
from surprise.model_selection import train_test_split
from surprise.accuracy import rmse

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
# LOAD DATA
# =========================

def load_ratings_dataframe():

    print("\nLoading ratings from MongoDB...")

    ratings_cursor = get_db()["ratings"].find()

    ratings_df = pd.DataFrame(list(ratings_cursor))

    return ratings_df


def load_movies_dataframe():

    movies_cursor = get_db()["movies"].find()

    movies_df = pd.DataFrame(list(movies_cursor))

    return movies_df


# =========================
# PREPARE SURPRISE DATASET
# =========================

def prepare_dataset(ratings_df):

    print("Preparing dataset for Surprise...")

    reader = Reader(rating_scale=(1, 5))

    data = Dataset.load_from_df(
        ratings_df[["userId", "movieId", "rating"]],
        reader
    )

    return data


# =========================
# TRAIN MODEL
# =========================

def train_model(data):

    print("\nTraining collaborative filtering model...")

    trainset, testset = train_test_split(
        data,
        test_size=0.2,
        random_state=42
    )

    # SVD model
    model = SVD()

    model.fit(trainset)

    predictions = model.test(testset)

    model_rmse = rmse(predictions)

    print(f"\nRMSE: {model_rmse:.4f}")

    return model


# =========================
# GENERATE RECOMMENDATIONS
# =========================

def recommend_movies_for_user(
    model,
    user_id,
    top_n=10
):

    print(f"\nGenerating recommendations for user {user_id}...")

    movies_df = load_movies_dataframe()

    ratings_df = load_ratings_dataframe()

    # Movies already rated by user
    watched_movies = ratings_df[
        ratings_df["userId"] == user_id
    ]["movieId"].tolist()

    # Candidate movies
    candidate_movies = movies_df[
        ~movies_df["movieId"].isin(watched_movies)
    ]

    predictions = []

    # Predict ratings
    for _, movie in candidate_movies.iterrows():

        movie_id = movie["movieId"]

        predicted_rating = model.predict(
            user_id,
            movie_id
        ).est

        predictions.append({
            "movieId": movie_id,
            "title": movie["title"],
            "genres": movie["genres"],
            "predicted_rating": predicted_rating
        })

    # Convert to dataframe
    predictions_df = pd.DataFrame(predictions)

    # Sort predictions
    predictions_df = predictions_df.sort_values(
        by="predicted_rating",
        ascending=False
    )

    # Top recommendations
    top_recommendations = predictions_df.head(top_n)

    return top_recommendations


# =========================
# SAVE RECOMMENDATIONS
# =========================

def save_recommendations(
    user_id,
    recommendations_df
):

    print("\nSaving recommendations into MongoDB...")

    recommendations_collection = get_db()["recommendations"]

    # Remove previous recommendations
    recommendations_collection.delete_many({
        "type": "collaborative",
        "userId": user_id
    })

    recommendations_list = []

    for _, row in recommendations_df.iterrows():

        recommendations_list.append({
            "movieId": int(row["movieId"]),
            "title": row["title"],
            "genres": row["genres"],
            "predicted_rating": round(
                row["predicted_rating"],
                2
            )
        })

    document = {
        "type": "collaborative",
        "userId": user_id,
        "recommendations": recommendations_list
    }

    recommendations_collection.insert_one(document)

    print("Recommendations saved successfully.")


# =========================
# DISPLAY RECOMMENDATIONS
# =========================

def display_recommendations(
    user_id,
    recommendations_df
):

    print("\n==============================")
    print(f" RECOMMENDATIONS FOR USER {user_id} ")
    print("==============================\n")

    for i, (_, row) in enumerate(recommendations_df.iterrows(), start=1):

        print(
            f"{i}. "
            f"{row['title']} | "
            f"Predicted Rating: "
            f"{row['predicted_rating']:.2f}"
        )

    print("\n==============================\n")


# =========================
# MAIN
# =========================

def main():

    USER_ID = 1

    ratings_df = load_ratings_dataframe()

    data = prepare_dataset(ratings_df)

    model = train_model(data)

    recommendations = recommend_movies_for_user(
        model,
        USER_ID,
        top_n=10
    )

    display_recommendations(
        USER_ID,
        recommendations
    )

    save_recommendations(
        USER_ID,
        recommendations
    )

    print(
        "\nCollaborative filtering completed successfully."
    )


if __name__ == "__main__":
    main()