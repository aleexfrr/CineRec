"""
Collaborative Filtering — SVD (Surprise)

Uso:
    python -m recommender.collaborative.collaborative_filtering --train
    python -m recommender.collaborative.collaborative_filtering --predict 42

--train   : Entrena SVD con todos los ratings y guarda el modelo en GridFS.
--predict : Carga el modelo de GridFS y genera recomendaciones para el usuario.
"""
import argparse
from pathlib import Path

import pandas as pd
from pymongo import MongoClient
from surprise import Dataset, Reader, SVD
from surprise.model_selection import train_test_split
from surprise.accuracy import rmse

import sys
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
from config import MONGO_URI, DATABASE_NAME
from recommender.model_store import save_model, load_model

MODEL_NAME = "model_collaborative"


# ── Conexión ──────────────────────────────────────────────────────────────────

_client = None

def get_db():
    global _client
    if _client is None:
        _client = MongoClient(MONGO_URI)
    return _client[DATABASE_NAME]


# ── Carga de datos ────────────────────────────────────────────────────────────

def load_ratings():
    print("Cargando ratings de MongoDB...")
    docs = list(get_db()["ratings"].find({}, {"userId": 1, "movieId": 1, "rating": 1}))
    return pd.DataFrame(docs)


def load_movies():
    docs = list(get_db()["movies"].find({}, {"movieId": 1, "title": 1, "genres": 1}))
    return pd.DataFrame(docs)


# ── Entrenamiento ─────────────────────────────────────────────────────────────

def train():
    print("\n=== ENTRENAMIENTO — Collaborative Filtering (SVD) ===\n")

    ratings_df = load_ratings()

    reader = Reader(rating_scale=(1, 5))
    data = Dataset.load_from_df(ratings_df[["userId", "movieId", "rating"]], reader)

    # Evaluamos con split 80/20 para tener métricas
    trainset_eval, testset = train_test_split(data, test_size=0.2, random_state=42)
    model_eval = SVD(random_state=42)
    model_eval.fit(trainset_eval)
    preds = model_eval.test(testset)
    model_rmse = rmse(preds, verbose=False)
    print(f"RMSE (evaluación): {model_rmse:.4f}")

    # Entrenamos sobre el dataset completo para predicciones en producción
    print("Entrenando sobre dataset completo...")
    full_trainset = data.build_full_trainset()
    model_full = SVD(random_state=42)
    model_full.fit(full_trainset)

    # Guardamos en GridFS
    save_model({"model": model_full, "rmse": round(model_rmse, 4)}, MODEL_NAME)

    # Guardamos métricas en MongoDB
    get_db()["model_metrics"].delete_many({"model": "collaborative"})
    get_db()["model_metrics"].insert_one({
        "model": "collaborative",
        "algorithm": "SVD",
        "rmse": round(model_rmse, 4)
    })
    print(f"\nEntrenamiento completado. RMSE = {model_rmse:.4f}")


# ── Predicción ────────────────────────────────────────────────────────────────

def predict(user_id: int, top_n: int = 10):
    print(f"\n=== PREDICCIÓN — Usuario {user_id} ===\n")

    data = load_model(MODEL_NAME)
    model = data["model"]

    ratings_df = load_ratings()
    movies_df  = load_movies()

    # Películas ya vistas por el usuario
    vistas = set(ratings_df[ratings_df["userId"] == user_id]["movieId"].tolist())

    # Predecir sobre todas las no vistas
    candidatos = movies_df[~movies_df["movieId"].isin(vistas)].copy()

    predicciones = []
    for _, row in candidatos.iterrows():
        pred = model.predict(user_id, row["movieId"]).est
        predicciones.append({
            "movieId": int(row["movieId"]),
            "title":   row["title"],
            "genres":  row["genres"],
            "predicted_rating": round(pred, 2)
        })

    predicciones.sort(key=lambda x: x["predicted_rating"], reverse=True)
    top = predicciones[:top_n]

    # Mostrar
    print(f"Top {top_n} recomendaciones para usuario {user_id}:")
    for i, r in enumerate(top, 1):
        print(f"  {i}. {r['title']} | Rating estimado: {r['predicted_rating']:.2f}")

    # Guardar en MongoDB
    col = get_db()["recommendations"]
    col.delete_many({"type": "collaborative", "userId": user_id})
    col.insert_one({
        "type": "collaborative",
        "userId": user_id,
        "recommendations": top
    })
    print(f"\nRecomendaciones guardadas en MongoDB.")
    return top


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Collaborative Filtering (SVD)")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--train",   action="store_true", help="Entrenar y guardar modelo")
    group.add_argument("--predict", type=int, metavar="USER_ID", help="Predecir para un usuario")
    parser.add_argument("--top", type=int, default=10, help="Número de recomendaciones (default: 10)")
    args = parser.parse_args()

    if args.train:
        train()
    else:
        predict(args.predict, args.top)
