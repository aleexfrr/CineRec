from datetime import datetime, timezone
from typing import Any, Optional
from bson import ObjectId
from pydantic import BaseModel, ConfigDict, Field, field_validator


# ObjectId es el id raro que usa MongoDB, esto lo convierte a string normal
class PyObjectId(str):
    @classmethod
    def __get_validators__(cls):
        yield cls.validar

    @classmethod
    def validar(cls, v: Any, _info: Any = None) -> str:
        if isinstance(v, ObjectId):
            return str(v)
        if ObjectId.is_valid(str(v)):
            return str(v)
        raise ValueError(f"ObjectId inválido: {v!r}")


# Como queda guardado el usuario en MongoDB
class UsuarioDB(BaseModel):
    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)

    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    nombre: str = Field(min_length=2, max_length=50)
    apellidos: str = Field(default="", max_length=100)
    edad: Optional[int] = Field(default=None, ge=13, le=120)
    genero: Optional[str] = Field(default=None, max_length=30)
    email: str = Field(pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
    password_hash: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    onboarding_done: bool = False
    preferred_groups: dict[str, int] = Field(default_factory=dict)

    # Lo que manda el frontend al registrarse
    # acepta 'name' (un campo) o 'nombre'+'apellidos' por separado
    class Crear(BaseModel):
        name: Optional[str] = None
        nombre: Optional[str] = None
        apellidos: str = Field(default="", max_length=100)
        edad: Optional[int] = Field(default=None, ge=13, le=120)
        genero: Optional[str] = Field(default=None, max_length=30)
        email: str = Field(pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
        password: str = Field(min_length=6, max_length=128)

        @field_validator("email")
        @classmethod
        def correo_minusculas(cls, v: str) -> str:
            return v.strip().lower()

        def get_nombre(self) -> str:
            """Devuelve el nombre sin importar si vino como 'name' o 'nombre'."""
            return (self.nombre or self.name or "").strip()

        def get_apellidos(self) -> str:
            return self.apellidos.strip()

    # Lo que manda el frontend al hacer login
    class Login(BaseModel):
        email: str
        password: str

        @field_validator("email")
        @classmethod
        def correo_minusculas(cls, v: str) -> str:
            return v.strip().lower()

    # Para editar el perfil, todos opcionales porque puede cambiar solo uno
    class Actualizar(BaseModel):
        nombre: Optional[str] = Field(default=None, min_length=2, max_length=50)
        apellidos: Optional[str] = Field(default=None, min_length=2, max_length=100)
        email: Optional[str] = Field(default=None, pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$")

    # Para cambiar la contraseña desde el perfil
    class CambiarPassword(BaseModel):
        password_actual: str
        password_nueva: str = Field(min_length=6, max_length=128)
        password_nueva2: str

        @field_validator("password_nueva2")
        @classmethod
        def passwords_coinciden(cls, v: str, info: Any) -> str:
            if "password_nueva" in info.data and v != info.data["password_nueva"]:
                raise ValueError("Las contraseñas nuevas no coinciden")
            return v

    # Los puntos del onboarding, valida que la suma sea exactamente 5
    class Preferencias(BaseModel):
        grupos: dict[str, int]

        @field_validator("grupos")
        @classmethod
        def validar_puntos(cls, v: dict[str, int]) -> dict[str, int]:
            if sum(v.values()) != 5:
                raise ValueError(f"La suma de puntos debe ser 5, recibido: {sum(v.values())}")
            if any(p < 0 for p in v.values()):
                raise ValueError("Los puntos no pueden ser negativos")
            return v

    # Devuelve los datos del usuario listos para mandar al frontend (sin password)
    def a_respuesta(self) -> dict:
        return {
            "id": str(self.id),
            "nombre": self.nombre,
            "apellidos": self.apellidos,
            "name": f"{self.nombre} {self.apellidos}",  # el frontend JS espera este campo
            "edad": self.edad,
            "genero": self.genero,
            "email": self.email,
            "created_at": self.created_at,
            "onboarding_done": self.onboarding_done,
            "preferred_groups": self.preferred_groups,
        }
