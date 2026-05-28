from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import conectar, cerrar
from app.routers import auth, peliculas


@asynccontextmanager
async def lifespan(app: FastAPI):
    await conectar()
    yield
    await cerrar()


app = FastAPI(title="CineRec API", lifespan=lifespan)

# permite peticiones desde el frontend (en producción limitar allow_origins)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router,      prefix="/api")
app.include_router(peliculas.router, prefix="/api")


@app.get("/")
async def root():
    return {"mensaje": "CineRec API funcionando"}
