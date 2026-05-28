"""
Classification Recommender — Random Forest

Predice la probabilidad de que un usuario le guste una película
combinando sus datos de perfil con las características del film.

Uso:
    python -m recommender.classification.classification_recommender --train
    python -m recommender.classification.classification_recommender --predict 42
"""
import argparse
import ast
from pathlib import Path

import pandas as pd
from pymongo import MongoClient
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, classification_report

import sys
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
from config import MONGO_URI, DATABASE_NAME
from recommender.model_store import save_model, load_model

MODEL_NAME = "model_classification"


# ── Conexión ──────────────────────────────────────────────────────────────────

_client = None

def get_db():
    global _client
    if _client is None:
        _client = MongoClient(MONGO_URI)
    return _client[DATABASE_NAME]


# ── Carga de datos ────────────────────────────────────────────────────────────

def load_dataframes():
    print("Cargando datos de MongoDB...")
    ratings_df = pd.DataFrame(list(get_db()["ratings"].find()))
    movies_df  = pd.DataFrame(list(get_db()["movies"].find()))
    users_df   = pd.DataFrame(list(get_db()["users"].find()))
    print(f"  Ratings: {len(ratings_df)} | Películas: {len(movies_df)} | Usuarios: {len(users_df)}")
    return ratings_df, movies_df, users_df


# ── Construcción del dataset ──────────────────────────────────────────────────

def build_dataset(ratings_df, movies_df, users_df):
    print("Construyendo dataset...")

    ratings_df = ratings_df.copy()
    movies_df  = movies_df.copy()
    users_df   = users_df.copy()

    ratings_df["liked"] = (ratings_df["rating"] >= 4).astype(int)

    movies_df["genres_parsed"] = movies_df["genres"].apply(
        lambda x: ast.literal_eval(x) if isinstance(x, str) else x
    )
    all_genres = sorted({g for gs in movies_df["genres_parsed"] for g in gs})

    for g in all_genres:
        movies_df[f"genre_{g}"] = movies_df["genres_parsed"].apply(
            lambda gs: 1 if g in gs else 0
        )

    le = LabelEncoder()
    users_df["gender_encoded"] = le.fit_transform(users_df["gender"])

    genre_cols   = [f"genre_{g}" for g in all_genres]
    feature_cols = ["userId", "movieId", "year", "age", "gender_encoded", "occupation"] + genre_cols

    df = ratings_df.merge(
        movies_df[["movieId", "year"] + genre_cols], on="movieId"
    ).merge(
        users_df[["userId", "age", "gender_encoded", "occupation"]], on="userId"
    )

    print(f"Dataset: {len(df)} muestras | Liked: {df['liked'].sum()} | Not liked: {(df['liked']==0).sum()}")
    return df, all_genres, feature_cols, le


# ── Entrenamiento ─────────────────────────────────────────────────────────────

def train():
    print("\n=== ENTRENAMIENTO — Classification (Random Forest) ===\n")

    ratings_df, movies_df, users_df = load_dataframes()
    df, all_genres, feature_cols, le = build_dataset(ratings_df, movies_df, users_df)

    X = df[feature_cols]
    y = df["liked"]

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    print(f"\nEntrenando Random Forest ({len(X_train)} muestras de entrenamiento)...")
    model = RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42, n_jobs=-1)
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    metrics = {
        "accuracy":  round(accuracy_score(y_test, y_pred),  4),
        "precision": round(precision_score(y_test, y_pred), 4),
        "recall":    round(recall_score(y_test, y_pred),    4),
        "f1_score":  round(f1_score(y_test, y_pred),        4),
    }

    print("\n--- Evaluación del modelo ---")
    for k, v in metrics.items():
        print(f"  {k.capitalize()}: {v:.4f}")
    print("\n" + classification_report(y_test, y_pred, target_names=["Not liked", "Liked"]))

    # Guardar modelo + metadatos necesarios para predecir
    save_model({
        "model":        model,
        "all_genres":   all_genres,
        "feature_cols": feature_cols,
        "gender_encoder": le,
    }, MODEL_NAME)

    # Métricas en MongoDB
    get_db()["model_metrics"].delete_many({"model": "classification"})
    get_db()["model_metrics"].insert_one({"model": "classification", "algorithm": "RandomForest", **metrics})

    print("Entrenamiento completado.")


# ── Predicción ────────────────────────────────────────────────────────────────

def predict(user_id: int, top_n: int = 10):
    print(f"\n=== PREDICCIÓN — Usuario {user_id} ===\n")

    data        = load_model(MODEL_NAME)
    model       = data["model"]
    all_genres  = data["all_genres"]
    feature_cols = data["feature_cols"]

    db = get_db()
    ratings_df = pd.DataFrame(list(db["ratings"].find()))
    movies_df  = pd.DataFrame(list(db["movies"].find()))
    users_df   = pd.DataFrame(list(db["users"].find()))

    user = users_df[users_df["userId"] == user_id]
    if user.empty:
        print(f"Usuario {user_id} no encontrado en el dataset.")
        return []
    user = user.iloc[0]

    # Películas ya vistas
    vistas = set(ratings_df[ratings_df["userId"] == user_id]["movieId"].astype(int).tolist())

    # Preparar candidatos
    movies_df = movies_df.copy()
    movies_df["genres_parsed"] = movies_df["genres"].apply(
        lambda x: ast.literal_eval(x) if isinstance(x, str) else x
    )
    for g in all_genres:
        movies_df[f"genre_{g}"] = movies_df["genres_parsed"].apply(lambda gs: 1 if g in gs else 0)

    candidatos = movies_df[~movies_df["movieId"].isin(vistas)].copy()
    candidatos["userId"]         = user_id
    candidatos["age"]            = user["age"]
    candidatos["gender_encoded"] = 1 if str(user.get("gender", "")).strip().upper() in ("M", "MALE", "H", "HOMBRE") else 0
    candidatos["occupation"]     = user["occupation"]

    probs = model.predict_proba(candidatos[feature_cols])[:, 1]
    candidatos = candidatos.copy()
    candidatos["like_probability"] = probs

    top_df = (
        candidatos[["movieId", "title", "genres", "like_probability"]]
        .sort_values("like_probability", ascending=False)
        .head(top_n)
    )

    top = [
        {
            "movieId":          int(r["movieId"]),
            "title":            r["title"],
            "genres":           r["genres"],
            "like_probability": round(float(r["like_probability"]), 4)
        }
        for _, r in top_df.iterrows()
    ]

    print(f"Top {top_n} predicciones para usuario {user_id}:")
    for i, r in enumerate(top, 1):
        print(f"  {i}. {r['title']} | P(gusta): {r['like_probability']:.2%}")

    # Guardar en MongoDB
    col = db["recommendations"]
    col.delete_many({"type": "classification", "userId": user_id})
    col.insert_one({"type": "classification", "userId": user_id, "recommendations": top})
    print("\nRecomendaciones guardadas en MongoDB.")
    return top


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Classification Recommender (Random Forest)")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--train",   action="store_true", help="Entrenar y guardar modelo")
    group.add_argument("--predict", type=int, metavar="USER_ID", help="Predecir para un usuario")
    parser.add_argument("--top", type=int, default=10, help="Número de recomendaciones (default: 10)")
    args = parser.parse_args()

    if args.train:
        train()
    else:
        predict(args.predict, args.top)
