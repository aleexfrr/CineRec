from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator


# Como queda guardada la película en MongoDB
class PeliculaDB(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    # usamos el movieId de MovieLens como _id para no tener duplicados al importar
    id: int = Field(alias="_id")
    title: str
    genres: list[str]

    # MovieLens trae los géneros como "Action|Comedy|Drama", aquí los separamos
    @field_validator("genres", mode="before")
    @classmethod
    def parsear_generos(cls, v: object) -> list[str]:
        if isinstance(v, str):
            if v == "(no genres listed)":
                return []
            return [g.strip() for g in v.split("|") if g.strip()]
        return v

    # Para insertar películas desde el script de importación del CSV
    class Crear(BaseModel):
        movie_id: int
        title: str
        genres: list[str] | str

        @field_validator("genres", mode="before")
        @classmethod
        def parsear_generos(cls, v: object) -> list[str]:
            if isinstance(v, str):
                if v == "(no genres listed)":
                    return []
                return [g.strip() for g in v.split("|") if g.strip()]
            return v

    # Filtros de la búsqueda: texto, género, año, rating mínimo y paginación
    class Filtro(BaseModel):
        q: Optional[str] = None
        genre: Optional[str] = None
        year: Optional[int] = None
        min_rating: Optional[float] = Field(default=None, ge=0.5, le=5.0)
        limit: int = Field(default=20, ge=1, le=100)
        skip: int = Field(default=0, ge=0)

    # Devuelve los datos listos para mandar al frontend
    def a_respuesta(self) -> dict:
        return {
            "movie_id": self.id,
            "title": self.title,
            "genres": self.genres,
        }


# Géneros oficiales del dataset MovieLens
GENRES_MOVIELENS: list[str] = [
    "Action", "Adventure", "Animation", "Children", "Comedy",
    "Crime", "Documentary", "Drama", "Fantasy", "Film-Noir",
    "Horror", "Musical", "Mystery", "Romance", "Sci-Fi",
    "Thriller", "War", "Western",
]
