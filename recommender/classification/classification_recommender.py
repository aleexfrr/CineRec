from pymongo import MongoClient
import pandas as pd
import ast
from pathlib import Path

from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    classification_report
)

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

def load_dataframes():

    print("\nLoading data from MongoDB...")

    ratings_df = pd.DataFrame(list(get_db()["ratings"].find()))
    movies_df = pd.DataFrame(list(get_db()["movies"].find()))
    users_df = pd.DataFrame(list(get_db()["users"].find()))

    print("Data loaded successfully.")

    return ratings_df, movies_df, users_df


# =========================
# PREPARE DATASET
# =========================

def prepare_dataset(ratings_df, movies_df, users_df):

    print("\nPreparing dataset...")

    # Binary label: 1 = liked (rating >= 4), 0 = not liked
    ratings_df["liked"] = (ratings_df["rating"] >= 4).astype(int)

    # Parse genres and extract all unique ones
    movies_df["genres_parsed"] = movies_df["genres"].apply(
        lambda x: ast.literal_eval(x) if isinstance(x, str) else x
    )

    all_genres = sorted(set(
        genre
        for genres in movies_df["genres_parsed"]
        for genre in genres
    ))

    # One-hot encode genres
    for genre in all_genres:
        movies_df[f"genre_{genre}"] = movies_df["genres_parsed"].apply(
            lambda genres: 1 if genre in genres else 0
        )

    # Encode gender
    le = LabelEncoder()
    users_df["gender_encoded"] = le.fit_transform(users_df["gender"])

    # Merge ratings + movies + users
    df = ratings_df.merge(
        movies_df[["movieId", "year"] + [f"genre_{g}" for g in all_genres]],
        on="movieId"
    )

    df = df.merge(
        users_df[["userId", "age", "gender_encoded", "occupation"]],
        on="userId"
    )

    print(f"Dataset ready: {len(df)} samples | "
            f"Liked: {df['liked'].sum()} | "
            f"Not liked: {(df['liked'] == 0).sum()}")

    return df, all_genres


# =========================
# TRAIN MODEL
# =========================

def train_model(df, all_genres):

    print("\nTraining Random Forest classifier...")

    genre_cols = [f"genre_{g}" for g in all_genres]

    feature_cols = [
        "userId", "movieId", "year",
        "age", "gender_encoded", "occupation"
    ] + genre_cols

    X = df[feature_cols]
    y = df["liked"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y,
        test_size=0.2,
        random_state=42
    )

    model = RandomForestClassifier(
        n_estimators=100,
        max_depth=10,
        random_state=42,
        n_jobs=-1
    )

    model.fit(X_train, y_train)

    # Evaluate
    y_pred = model.predict(X_test)

    accuracy  = accuracy_score(y_test, y_pred)
    precision = precision_score(y_test, y_pred)
    recall    = recall_score(y_test, y_pred)
    f1        = f1_score(y_test, y_pred)

    print("\n--- Model Evaluation ---")
    print(f"Accuracy:  {accuracy:.4f}")
    print(f"Precision: {precision:.4f}")
    print(f"Recall:    {recall:.4f}")
    print(f"F1 Score:  {f1:.4f}")
    print("\nClassification Report:")
    print(classification_report(y_test, y_pred,
                                target_names=["Not liked", "Liked"]))

    metrics = {
        "accuracy":  round(accuracy,  4),
        "precision": round(precision, 4),
        "recall":    round(recall,    4),
        "f1_score":  round(f1,        4)
    }

    return model, metrics, feature_cols


# =========================
# PREDICT FOR USER
# =========================

def predict_for_user(model, user_id, movies_df, users_df, all_genres, feature_cols, top_n=10):

    print(f"\nGenerating liked predictions for user {user_id}...")

    user = users_df[users_df["userId"] == user_id]

    if user.empty:
        print(f"User {user_id} not found.")
        return None

    user = user.iloc[0]

    genre_cols = [f"genre_{g}" for g in all_genres]

    movies_df["genres_parsed"] = movies_df["genres"].apply(
        lambda x: ast.literal_eval(x) if isinstance(x, str) else x
    )

    for genre in all_genres:
        movies_df[f"genre_{genre}"] = movies_df["genres_parsed"].apply(
            lambda genres: 1 if genre in genres else 0
        )

    candidates = movies_df.copy()
    candidates["userId"]         = user_id
    candidates["age"]            = user["age"]
    candidates["gender_encoded"] = 1 if user["gender"] == "Male" else 0
    candidates["occupation"]     = user["occupation"]

    X_candidates = candidates[feature_cols]

    probabilities = model.predict_proba(X_candidates)[:, 1]

    candidates = candidates.copy()
    candidates["like_probability"] = probabilities

    top = (
        candidates[["movieId", "title", "genres", "like_probability"]]
        .sort_values("like_probability", ascending=False)
        .head(top_n)
        .reset_index(drop=True)
    )

    return top


# =========================
# SAVE RESULTS
# =========================

def save_results(user_id, predictions_df, metrics):

    print("\nSaving results into MongoDB...")

    db = get_db()

    # Save model metrics
    db.model_metrics.delete_many({ "model": "classification" })
    db.model_metrics.insert_one({
        "model": "classification",
        "algorithm": "RandomForest",
        **metrics
    })

    # Save predictions
    db.recommendations.delete_many({
        "type": "classification",
        "userId": user_id
    })

    recommendations_list = [
        {
            "movieId": int(row["movieId"]),
            "title": row["title"],
            "genres": row["genres"],
            "like_probability": round(float(row["like_probability"]), 4)
        }
        for _, row in predictions_df.iterrows()
    ]

    db.recommendations.insert_one({
        "type": "classification",
        "userId": user_id,
        "recommendations": recommendations_list
    })

    print("Results saved successfully.")


# =========================
# DISPLAY RESULTS
# =========================

def display_predictions(user_id, predictions_df):

    print("\n==============================")
    print(f" LIKED PREDICTIONS FOR USER {user_id} ")
    print("==============================\n")

    for i, (_, row) in enumerate(predictions_df.iterrows(), start=1):
        print(
            f"{i}. {row['title']} | "
            f"Probability of liking: {row['like_probability']:.2%}"
        )

    print("\n==============================\n")


# =========================
# MAIN
# =========================

def main():

    USER_ID = 1

    ratings_df, movies_df, users_df = load_dataframes()

    df, all_genres = prepare_dataset(ratings_df, movies_df, users_df)

    model, metrics, feature_cols = train_model(df, all_genres)

    predictions = predict_for_user(
        model, USER_ID,
        movies_df, users_df,
        all_genres, feature_cols,
        top_n=10
    )

    if predictions is not None:
        display_predictions(USER_ID, predictions)
        save_results(USER_ID, predictions, metrics)

    print("\nClassification recommender completed successfully.")


if __name__ == "__main__":
    main()
