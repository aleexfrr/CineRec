"""
Content-Based Filtering — TF-IDF + Cosine Similarity

La predicción agrega la similitud de todas las películas valoradas por el usuario,
ponderadas por su rating, y recomienda las más similares no vistas.

Uso:
    python -m recommender.content_based.content_based --train
    python -m recommender.content_based.content_based --predict 42
"""
import argparse
import ast
from pathlib import Path

import numpy as np
import pandas as pd
from pymongo import MongoClient
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from scipy.sparse import csr_matrix

import sys
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
from config import MONGO_URI, DATABASE_NAME
from recommender.model_store import save_model, load_model

MODEL_NAME = "model_content_based"


# ── Conexión ──────────────────────────────────────────────────────────────────

_client = None

def get_db():
    global _client
    if _client is None:
        _client = MongoClient(MONGO_URI)
    return _client[DATABASE_NAME]


# ── Carga de datos ────────────────────────────────────────────────────────────

def load_movies():
    print("Cargando películas de MongoDB...")
    docs = list(get_db()["movies"].find({}, {"movieId": 1, "title": 1, "genres": 1}))
    df = pd.DataFrame(docs)
    df["genres"] = df["genres"].apply(
        lambda x: ast.literal_eval(x) if isinstance(x, str) else x
    )
    df["genres_text"] = df["genres"].apply(
        lambda g: " ".join(g) if isinstance(g, list) else ""
    )
    return df.reset_index(drop=True)


def load_ratings():
    docs = list(get_db()["ratings"].find({}, {"userId": 1, "movieId": 1, "rating": 1}))
    return pd.DataFrame(docs)


# ── Entrenamiento ─────────────────────────────────────────────────────────────

def train():
    print("\n=== ENTRENAMIENTO — Content-Based (TF-IDF) ===\n")

    movies_df = load_movies()

    print("Construyendo matriz TF-IDF...")
    vectorizer = TfidfVectorizer(stop_words="english")
    tfidf_matrix = vectorizer.fit_transform(movies_df["genres_text"])

    # movie_id → posición en la matriz
    movie_id_to_idx = {
        int(row["movieId"]): idx
        for idx, row in movies_df.iterrows()
    }

    save_model({
        "vectorizer":    vectorizer,
        "tfidf_matrix":  tfidf_matrix,   # scipy sparse — eficiente en memoria
        "movie_id_to_idx": movie_id_to_idx,
        "movie_ids":     movies_df["movieId"].astype(int).tolist(),
        "titles":        movies_df["title"].tolist(),
        "genres":        movies_df["genres"].tolist(),
    }, MODEL_NAME)

    print(f"Matriz TF-IDF: {tfidf_matrix.shape[0]} películas × {tfidf_matrix.shape[1]} términos")
    print("\nEntrenamiento completado.")


# ── Predicción ────────────────────────────────────────────────────────────────

def predict(user_id: int, top_n: int = 10):
    print(f"\n=== PREDICCIÓN — Usuario {user_id} ===\n")

    data        = load_model(MODEL_NAME)
    tfidf       = data["tfidf_matrix"]
    id_to_idx   = data["movie_id_to_idx"]
    movie_ids   = data["movie_ids"]
    titles      = data["titles"]
    genres      = data["genres"]

    ratings_df = load_ratings()
    user_ratings = ratings_df[ratings_df["userId"] == user_id]

    if user_ratings.empty:
        print(f"El usuario {user_id} no tiene ratings. Sin recomendaciones.")
        return []

    # Perfil del usuario: vector agregado ponderado por rating
    # profile = Σ (rating_i / max_rating) * tfidf_vector_i
    profile = np.zeros(tfidf.shape[1])
    for _, row in user_ratings.iterrows():
        idx = id_to_idx.get(int(row["movieId"]))
        if idx is not None:
            weight = row["rating"] / 5.0
            profile += weight * tfidf[idx].toarray().flatten()

    if profile.sum() == 0:
        print("Perfil del usuario vacío (ninguna película valorada existe en el modelo).")
        return []

    profile_norm = profile / np.linalg.norm(profile)

    # Similitud del perfil contra todas las películas
    scores = cosine_similarity(profile_norm.reshape(1, -1), tfidf).flatten()

    # Excluir películas ya vistas
    vistas = set(user_ratings["movieId"].astype(int).tolist())
    recomendaciones = []
    for i, score in enumerate(scores):
        mid = int(movie_ids[i])
        if mid not in vistas:
            recomendaciones.append({
                "movieId":         mid,
                "title":           titles[i],
                "genres":          genres[i],
                "similarity_score": round(float(score), 4)
            })

    recomendaciones.sort(key=lambda x: x["similarity_score"], reverse=True)
    top = recomendaciones[:top_n]

    # Mostrar
    print(f"Top {top_n} recomendaciones para usuario {user_id}:")
    for i, r in enumerate(top, 1):
        print(f"  {i}. {r['title']} | Similitud: {r['similarity_score']:.4f}")

    # Guardar en MongoDB
    col = get_db()["recommendations"]
    col.delete_many({"type": "content_based", "userId": user_id})
    col.insert_one({
        "type": "content_based",
        "userId": user_id,
        "recommendations": top
    })
    print(f"\nRecomendaciones guardadas en MongoDB.")
    return top


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Content-Based Filtering (TF-IDF)")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--train",   action="store_true", help="Entrenar y guardar modelo")
    group.add_argument("--predict", type=int, metavar="USER_ID", help="Predecir para un usuario")
    parser.add_argument("--top", type=int, default=10, help="Número de recomendaciones (default: 10)")
    args = parser.parse_args()

    if args.train:
        train()
    else:
        predict(args.predict, args.top)
