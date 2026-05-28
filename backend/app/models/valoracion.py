from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.usuario import PyObjectId


class ValoracionDB(BaseModel):
    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)

    id:        Optional[PyObjectId] = Field(default=None, alias="_id")
    user_id:   str                  # str del ObjectId del usuario
    movie_id:  int
    rating:    float = Field(ge=0.5, le=5.0)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator("rating")
    @classmethod
    def redondear_medio_punto(cls, v: float) -> float:
        redondeado = round(v * 2) / 2
        if abs(redondeado - v) > 0.01:
            raise ValueError(f"El rating debe ser múltiplo de 0.5, recibido: {v}")
        return redondeado

    class Crear(BaseModel):
        movie_id: int
        rating: float = Field(ge=0.5, le=5.0)

        @field_validator("rating")
        @classmethod
        def redondear_medio_punto(cls, v: float) -> float:
            return round(v * 2) / 2

    class Stats(BaseModel):
        movie_id:           int
        total_valoraciones: int
        rating_promedio:    float
        rating_minimo:      float
        rating_maximo:      float
        distribucion:       dict[str, int]

    def a_respuesta(self) -> dict:
        return {
            "id":       str(self.id),
            "user_id":  self.user_id,
            "movie_id": self.movie_id,
            "rating":   self.rating,
            "timestamp": self.timestamp,
        }


def unix_a_datetime(unix_ts: int) -> datetime:
    return datetime.fromtimestamp(unix_ts, tz=timezone.utc)
