import motor.motor_asyncio
from app.config import MONGO_URL, DB_NAME

# Cliente de MongoDB (motor es la versión async de pymongo, necesaria para FastAPI)
cliente = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URL)

# Base de datos
db = cliente[DB_NAME]

# Colecciones — una por cada modelo
usuarios     = db["usuarios"]
peliculas    = db["peliculas"]
valoraciones = db["valoraciones"]

# Base de datos ML (datasets MovieLens + datos en tiempo real de la web)
db_ml = cliente["movie_recommender"]


async def conectar():
    """Comprueba que MongoDB está levantado. Se llama al arrancar la app."""
    await cliente.admin.command("ping")
    print(f"Conectado a MongoDB en {MONGO_URL} → base de datos '{DB_NAME}'")


async def cerrar():
    """Cierra la conexión. Se llama al apagar la app."""
    cliente.close()
