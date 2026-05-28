"""
Utilidades para guardar y cargar modelos en MongoDB GridFS.
Los modelos se serializan con joblib y se almacenan como ficheros binarios.
Esto permite que los modelos persistan entre reinicios del contenedor Docker.
"""
import io
import joblib
import gridfs
from pathlib import Path
from pymongo import MongoClient

import sys
sys.path.append(str(Path(__file__).resolve().parent.parent))
from config import MONGO_URI, DATABASE_NAME


def _get_fs():
    client = MongoClient(MONGO_URI)
    db = client[DATABASE_NAME]
    return gridfs.GridFS(db)


def save_model(model_data: dict, name: str) -> None:
    """Serializa model_data con joblib y lo guarda en GridFS."""
    fs = _get_fs()
    # Eliminar versión anterior si existe
    for old in fs.find({"filename": name}):
        fs.delete(old._id)
    buf = io.BytesIO()
    joblib.dump(model_data, buf)
    buf.seek(0)
    fs.put(buf, filename=name)
    print(f"[GridFS] Modelo '{name}' guardado correctamente.")


def load_model(name: str) -> dict:
    """Carga y deserializa un modelo desde GridFS."""
    fs = _get_fs()
    f = fs.find_one({"filename": name}, sort=[("uploadDate", -1)])
    if f is None:
        raise FileNotFoundError(
            f"Modelo '{name}' no encontrado en GridFS. "
            f"Ejecuta primero: python -m recommender.<modulo> --train"
        )
    buf = io.BytesIO(f.read())
    return joblib.load(buf)


def model_exists(name: str) -> bool:
    """Devuelve True si el modelo ya está guardado en GridFS."""
    fs = _get_fs()
    return fs.find_one({"filename": name}) is not None
