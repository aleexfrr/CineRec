from pymongo import MongoClient
import pandas as pd
import numpy as np
import ast
from pathlib import Path

from surprise import Dataset, Reader, SVD
from surprise.model_selection import train_test_split as surprise_split

from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

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

def load_data():

    print("\nLoading data from MongoDB...")

    ratings_df = pd.DataFrame(list(get_db()["ratings"].find()))
    movies_df  = pd.DataFrame(list(get_db()["movies"].find()))
    users_df   = pd.DataFrame(list(get_db()["users"].find()))

    print(f"Ratings: {len(ratings_df)} | Movies: {len(movies_df)} | Users: {len(users_df)}")

    return ratings_df, movies_df, users_df


# =========================
# TRAIN / TEST SPLIT
# =========================

def split_data(ratings_df, test_size=0.2, random_state=42):
    """
    Split per user: last 20% of each user's ratings go to test set.
    This simulates a real recommendation scenario.
    """

    print("\nSplitting data into train / test...")

    ratings_df = ratings_df.sort_values(["userId", "timestamp"])

    train_list = []
    test_list  = []

    for _, user_ratings in ratings_df.groupby("userId"):

        n = len(user_ratings)
        n_test = max(1, int(n * test_size))

        train_list.append(user_ratings.iloc[:-n_test])
        test_list.append(user_ratings.iloc[-n_test:])

    train_df = pd.concat(train_list).reset_index(drop=True)
    test_df  = pd.concat(test_list).reset_index(drop=True)

    print(f"Train: {len(train_df)} | Test: {len(test_df)}")

    return train_df, test_df


# =========================
# METRICS
# =========================

def precision_at_k(recommended, relevant, k):
    recommended_k = recommended[:k]
    hits = len(set(recommended_k) & set(relevant))
    return hits / k if k > 0 else 0.0


def recall_at_k(recommended, relevant, k):
    recommended_k = recommended[:k]
    hits = len(set(recommended_k) & set(relevant))
    return hits / len(relevant) if len(relevant) > 0 else 0.0


def ndcg_at_k(recommended, relevant, k):
    recommended_k = recommended[:k]
    dcg = sum(
        1 / np.log2(i + 2)
        for i, item in enumerate(recommended_k)
        if item in relevant
    )
    idcg = sum(
        1 / np.log2(i + 2)
        for i in range(min(len(relevant), k))
    )
    return dcg / idcg if idcg > 0 else 0.0


def evaluate_recommendations(user_recommendations, test_df, k=10):
    """
    Given a dict {user_id: [movieId, ...]} of recommendations,
    compute Precision@K, Recall@K and NDCG@K against the test set.
    Only users with liked items (rating >= 4) in test are evaluated.
    """

    precisions = []
    recalls    = []
    ndcgs      = []

    liked_test = test_df[test_df["rating"] >= 4]

    for user_id, recommended_movies in user_recommendations.items():

        relevant = liked_test[
            liked_test["userId"] == user_id
        ]["movieId"].tolist()

        if not relevant:
            continue

        precisions.append(precision_at_k(recommended_movies, relevant, k))
        recalls.append(recall_at_k(recommended_movies, relevant, k))
        ndcgs.append(ndcg_at_k(recommended_movies, relevant, k))

    return {
        f"Precision@{k}": round(np.mean(precisions), 4),
        f"Recall@{k}":    round(np.mean(recalls),    4),
        f"NDCG@{k}":      round(np.mean(ndcgs),      4),
    }


# =========================
# COLLABORATIVE FILTERING
# =========================

def evaluate_collaborative(train_df, test_df, movies_df, k=10, n_users=200):

    print("\n[1/4] Evaluating Collaborative Filtering (SVD)...")

    reader = Reader(rating_scale=(1, 5))
    data = Dataset.load_from_df(
        train_df[["userId", "movieId", "rating"]],
        reader
    )

    trainset = data.build_full_trainset()
    model = SVD(random_state=42)
    model.fit(trainset)

    # Evaluate on a sample of users for speed
    sample_users = test_df["userId"].unique()[:n_users]

    user_recommendations = {}

    for user_id in sample_users:

        watched = train_df[
            train_df["userId"] == user_id
        ]["movieId"].tolist()

        candidates = movies_df[
            ~movies_df["movieId"].isin(watched)
        ]["movieId"].tolist()

        preds = [
            (movie_id, model.predict(user_id, movie_id).est)
            for movie_id in candidates
        ]

        preds.sort(key=lambda x: x[1], reverse=True)

        user_recommendations[user_id] = [p[0] for p in preds[:k]]

    metrics = evaluate_recommendations(user_recommendations, test_df, k)
    print(f"  Done. {metrics}")
    return metrics


# =========================
# CONTENT-BASED
# =========================

def evaluate_content_based(train_df, test_df, movies_df, k=10, n_users=200):

    print("\n[2/4] Evaluating Content-Based (TF-IDF)...")

    # Build TF-IDF matrix
    movies = movies_df.copy()
    movies["genres_parsed"] = movies["genres"].apply(
        lambda x: ast.literal_eval(x) if isinstance(x, str) else x
    )
    movies["genres_text"] = movies["genres_parsed"].apply(
        lambda g: " ".join(g)
    )
    movies = movies.reset_index(drop=True)

    tfidf = TfidfVectorizer(stop_words="english")
    tfidf_matrix = tfidf.fit_transform(movies["genres_text"])
    similarity_matrix = cosine_similarity(tfidf_matrix)

    movie_id_to_idx = {
        row["movieId"]: idx
        for idx, row in movies.iterrows()
    }

    sample_users = test_df["userId"].unique()[:n_users]

    user_recommendations = {}

    for user_id in sample_users:

        watched_ids = train_df[
            train_df["userId"] == user_id
        ]["movieId"].tolist()

        if not watched_ids:
            continue

        # Aggregate similarity scores from all watched movies
        scores = np.zeros(len(movies))

        for movie_id in watched_ids:
            idx = movie_id_to_idx.get(movie_id)
            if idx is not None:
                scores += similarity_matrix[idx]

        # Exclude already watched
        watched_idxs = [
            movie_id_to_idx[m]
            for m in watched_ids
            if m in movie_id_to_idx
        ]
        scores[watched_idxs] = -1

        top_idxs = np.argsort(scores)[::-1][:k]
        recommended = movies.iloc[top_idxs]["movieId"].tolist()

        user_recommendations[user_id] = recommended

    metrics = evaluate_recommendations(user_recommendations, test_df, k)
    print(f"  Done. {metrics}")
    return metrics


# =========================
# POPULARITY
# =========================

def evaluate_popularity(train_df, test_df, movies_df, k=10, n_users=200):

    print("\n[3/4] Evaluating Popularity Recommender...")

    # Top K popular movies from training set
    movie_stats = (
        train_df
        .groupby("movieId")
        .agg(
            average_rating=("rating", "mean"),
            rating_count=("rating", "count")
        )
        .reset_index()
    )

    top_popular = (
        movie_stats[movie_stats["rating_count"] >= 50]
        .sort_values("average_rating", ascending=False)
        .head(k)["movieId"]
        .tolist()
    )

    sample_users = test_df["userId"].unique()[:n_users]

    # Same list for every user (popularity is not personalized)
    user_recommendations = {
        user_id: top_popular
        for user_id in sample_users
    }

    metrics = evaluate_recommendations(user_recommendations, test_df, k)
    print(f"  Done. {metrics}")
    return metrics


# =========================
# CLASSIFICATION
# =========================

def evaluate_classification(train_df, test_df, movies_df, users_df, k=10, n_users=200):

    print("\n[4/4] Evaluating Classification (Random Forest)...")

    # Prepare features
    movies = movies_df.copy()
    movies["genres_parsed"] = movies["genres"].apply(
        lambda x: ast.literal_eval(x) if isinstance(x, str) else x
    )

    all_genres = sorted(set(
        genre
        for genres in movies["genres_parsed"]
        for genre in genres
    ))

    for genre in all_genres:
        movies[f"genre_{genre}"] = movies["genres_parsed"].apply(
            lambda genres: 1 if genre in genres else 0
        )

    le = LabelEncoder()
    users_df = users_df.copy()
    users_df["gender_encoded"] = le.fit_transform(users_df["gender"])

    genre_cols   = [f"genre_{g}" for g in all_genres]
    feature_cols = ["userId", "movieId", "year", "age", "gender_encoded", "occupation"] + genre_cols

    # Build training set
    df_train = train_df.merge(
        movies[["movieId", "year"] + genre_cols], on="movieId"
    ).merge(
        users_df[["userId", "age", "gender_encoded", "occupation"]], on="userId"
    )

    df_train["liked"] = (df_train["rating"] >= 4).astype(int)

    X_train = df_train[feature_cols]
    y_train = df_train["liked"]

    model = RandomForestClassifier(
        n_estimators=50,
        max_depth=8,
        random_state=42,
        n_jobs=-1
    )
    model.fit(X_train, y_train)

    # Generate recommendations for sample users
    sample_users = test_df["userId"].unique()[:n_users]
    user_recommendations = {}

    for user_id in sample_users:

        user = users_df[users_df["userId"] == user_id]
        if user.empty:
            continue
        user = user.iloc[0]

        watched = train_df[train_df["userId"] == user_id]["movieId"].tolist()
        candidates = movies[~movies["movieId"].isin(watched)].copy()

        candidates["userId"]         = user_id
        candidates["age"]            = user["age"]
        candidates["gender_encoded"] = user["gender_encoded"]
        candidates["occupation"]     = user["occupation"]

        X_candidates = candidates[feature_cols]
        probs = model.predict_proba(X_candidates)[:, 1]

        candidates = candidates.copy()
        candidates["prob"] = probs

        top = (
            candidates.sort_values("prob", ascending=False)
            .head(k)["movieId"]
            .tolist()
        )

        user_recommendations[user_id] = top

    metrics = evaluate_recommendations(user_recommendations, test_df, k)
    print(f"  Done. {metrics}")
    return metrics


# =========================
# DISPLAY & SAVE RESULTS
# =========================

def display_results(results, k):

    print(f"\n{'='*55}")
    print(f"  MODEL EVALUATION RESULTS — Top {k} Recommendations")
    print(f"{'='*55}")
    print(f"{'Model':<22} {'Precision@'+str(k):<16} {'Recall@'+str(k):<14} {'NDCG@'+str(k)}")
    print(f"{'-'*55}")

    for model_name, metrics in results.items():
        p = metrics[f"Precision@{k}"]
        r = metrics[f"Recall@{k}"]
        n = metrics[f"NDCG@{k}"]
        print(f"{model_name:<22} {p:<16} {r:<14} {n}")

    print(f"{'='*55}\n")


def save_results(results, k):

    print("Saving evaluation results to MongoDB...")

    db = get_db()
    db.evaluation_results.delete_many({})

    documents = [
        {
            "model": model_name,
            f"precision_at_{k}": metrics[f"Precision@{k}"],
            f"recall_at_{k}":    metrics[f"Recall@{k}"],
            f"ndcg_at_{k}":      metrics[f"NDCG@{k}"],
            "k": k
        }
        for model_name, metrics in results.items()
    ]

    db.evaluation_results.insert_many(documents)
    print("Evaluation results saved.")


# =========================
# MAIN
# =========================

def main():

    K = 10
    N_USERS = 200

    ratings_df, movies_df, users_df = load_data()

    train_df, test_df = split_data(ratings_df)

    results = {}

    results["Collaborative (SVD)"]    = evaluate_collaborative(train_df, test_df, movies_df, K, N_USERS)
    results["Content-Based (TF-IDF)"] = evaluate_content_based(train_df, test_df, movies_df, K, N_USERS)
    results["Popularity"]             = evaluate_popularity(train_df, test_df, movies_df, K, N_USERS)
    results["Classification (RF)"]    = evaluate_classification(train_df, test_df, movies_df, users_df, K, N_USERS)

    display_results(results, K)

    save_results(results, K)

    print("Evaluation completed successfully.")


if __name__ == "__main__":
    main()
