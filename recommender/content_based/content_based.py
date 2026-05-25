from pymongo import MongoClient
import pandas as pd
import ast
from pathlib import Path
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
# LOAD MOVIES
# =========================

def load_movies_dataframe():

    print("\nLoading movies from MongoDB...")

    movies_cursor = get_db()["movies"].find()

    movies_df = pd.DataFrame(list(movies_cursor))

    return movies_df


# =========================
# PREPROCESS GENRES
# =========================

def preprocess_movies(movies_df):

    print("Preprocessing movie genres...")

    movies = movies_df.copy()

    # Convert genres to string
    movies["genres"] = movies["genres"].apply(
        lambda x: ast.literal_eval(x)
        if isinstance(x, str)
        else x
    )

    movies["genres_text"] = movies["genres"].apply(
        lambda genres: " ".join(genres)
    )

    # Reset index to guarantee positional alignment with similarity matrix
    movies = movies.reset_index(drop=True)

    return movies


# =========================
# CREATE TF-IDF MATRIX
# =========================

def create_tfidf_matrix(movies_df):

    print("Creating TF-IDF matrix...")

    tfidf = TfidfVectorizer(stop_words="english")

    tfidf_matrix = tfidf.fit_transform(
        movies_df["genres_text"]
    )

    return tfidf_matrix


# =========================
# COMPUTE COSINE SIMILARITY
# =========================

def compute_similarity(tfidf_matrix):

    print("Computing cosine similarity...")

    similarity_matrix = cosine_similarity(tfidf_matrix)

    return similarity_matrix


# =========================
# GET MOVIE INDEX
# =========================

def get_movie_index(movies_df, movie_title):

    matches = movies_df[
        movies_df["title"].str.lower() == movie_title.lower()
    ]

    if matches.empty:
        return None

    # Devuelve la posición real en el DataFrame (no el label del índice)
    return movies_df.index.get_loc(matches.index[0])


# =========================
# RECOMMEND SIMILAR MOVIES
# =========================

def recommend_similar_movies(
    movie_title,
    movies_df,
    similarity_matrix,
    top_n=10
):

    print(f"\nGenerating recommendations for:")
    print(f"{movie_title}")

    movie_index = get_movie_index(
        movies_df,
        movie_title
    )

    if movie_index is None:

        print("\nMovie not found.")

        return None

    # Similarity scores
    similarity_scores = list(
        enumerate(similarity_matrix[movie_index])
    )

    # Sort by similarity
    similarity_scores = sorted(
        similarity_scores,
        key=lambda x: x[1],
        reverse=True
    )

    # Remove same movie
    similarity_scores = similarity_scores[1:]

    # Top similar movies
    top_movies = similarity_scores[:top_n]

    recommendations = []

    for movie_idx, similarity_score in top_movies:

        movie = movies_df.iloc[movie_idx]

        recommendations.append({
            "movieId": int(movie["movieId"]),
            "title": movie["title"],
            "genres": movie["genres"],
            "similarity_score": round(
                float(similarity_score),
                4
            )
        })

    recommendations_df = pd.DataFrame(recommendations)

    return recommendations_df


# =========================
# SAVE RECOMMENDATIONS
# =========================

def save_recommendations(
    movie_title,
    recommendations_df
):

    print("\nSaving recommendations into MongoDB...")

    recommendations_collection = get_db()["recommendations"]

    recommendations_collection.delete_many({
        "type": "content_based",
        "source_movie": movie_title
    })

    recommendations_list = recommendations_df.to_dict(
        "records"
    )

    document = {
        "type": "content_based",
        "source_movie": movie_title,
        "recommendations": recommendations_list
    }

    recommendations_collection.insert_one(document)

    print("Recommendations saved successfully.")


# =========================
# DISPLAY RECOMMENDATIONS
# =========================

def display_recommendations(
    movie_title,
    recommendations_df
):

    print("\n==============================")
    print(" CONTENT-BASED RECOMMENDATIONS ")
    print("==============================\n")

    print(f"Movie selected: {movie_title}\n")

    for i, (_, row) in enumerate(recommendations_df.iterrows(), start=1):

        print(
            f"{i}. "
            f"{row['title']} | "
            f"Similarity: "
            f"{row['similarity_score']:.4f}"
        )

    print("\n==============================\n")


# =========================
# MAIN
# =========================

def main():

    MOVIE_TITLE = "Toy Story"

    movies_df = load_movies_dataframe()

    movies_df = preprocess_movies(movies_df)

    tfidf_matrix = create_tfidf_matrix(
        movies_df
    )

    similarity_matrix = compute_similarity(
        tfidf_matrix
    )

    recommendations = recommend_similar_movies(
        MOVIE_TITLE,
        movies_df,
        similarity_matrix,
        top_n=10
    )

    if recommendations is not None:

        display_recommendations(
            MOVIE_TITLE,
            recommendations
        )

        save_recommendations(
            MOVIE_TITLE,
            recommendations
        )

    print(
        "\nContent-based recommender completed successfully."
    )


if __name__ == "__main__":
    main()