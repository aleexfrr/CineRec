from datetime import datetime, timedelta, timezone
from bson import ObjectId
import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError

from app.config import SECRET_KEY, ALGORITHM, TOKEN_DIAS
from app.database import usuarios

_bearer = HTTPBearer()


def hashear_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verificar_password(password: str, hash: str) -> bool:
    return bcrypt.checkpw(password.encode(), hash.encode())


def crear_token(user_id: str) -> str:
    expira = datetime.now(timezone.utc) + timedelta(days=TOKEN_DIAS)
    return jwt.encode({"sub": user_id, "exp": expira}, SECRET_KEY, algorithm=ALGORITHM)


async def usuario_actual(creds: HTTPAuthorizationCredentials = Depends(_bearer)):
    """Dependencia de FastAPI: extrae y valida el token JWT de la cabecera Authorization."""
    try:
        payload  = jwt.decode(creds.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user_id  = payload.get("sub")
        if not user_id:
            raise ValueError
    except (JWTError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")

    user = await usuarios.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario no encontrado")
    return user
