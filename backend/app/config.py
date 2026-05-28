import os
from pathlib import Path
from dotenv import load_dotenv

# El .env está en la raíz del proyecto (dos niveles por encima de backend/app/)
load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")

MONGO_URL  = os.getenv("MONGO_URL",  "mongodb://localhost:27017")
DB_NAME    = os.getenv("DB_NAME",    "cinerec")
SECRET_KEY = os.getenv("SECRET_KEY", "cinerec-dev-secret-cambiame-en-produccion")
ALGORITHM  = "HS256"
TOKEN_DIAS = 30
