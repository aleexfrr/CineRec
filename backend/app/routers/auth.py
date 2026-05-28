from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status

from app.auth_utils import hashear_password, verificar_password, crear_token, usuario_actual
from app.database import usuarios, db_ml
from app.models import UsuarioDB
from app.ml_sync import sync_new_user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", status_code=201)
async def register(datos: UsuarioDB.Crear):
    # comprobar que el email no está ya registrado
    if await usuarios.find_one({"email": datos.email}):
        raise HTTPException(status_code=400, detail="Este correo ya está registrado")

    nombre    = datos.get_nombre()
    apellidos = datos.get_apellidos()

    doc = UsuarioDB(
        nombre=nombre or "Usuario",
        apellidos=apellidos,
        edad=datos.edad,
        genero=datos.genero,
        email=datos.email,
        password_hash=hashear_password(datos.password),
    )
    resultado = await usuarios.insert_one(doc.model_dump(by_alias=True, exclude={"id"}))
    user_id = str(resultado.inserted_id)

    # Sincronizar con el dataset ML para que NodeRED lo capture
    ml_user_id = await sync_new_user(
        {"_id": resultado.inserted_id, "nombre": nombre,
         "genero": datos.genero, "edad": datos.edad},
        db_ml,
    )
    if ml_user_id:
        await usuarios.update_one(
            {"_id": resultado.inserted_id},
            {"$set": {"ml_user_id": ml_user_id}},
        )

    return {
        "token":   crear_token(user_id),
        "user_id": user_id,
        "name":    f"{nombre} {apellidos}".strip(),
        "email":   datos.email,
    }


@router.post("/login")
async def login(datos: UsuarioDB.Login):
    user = await usuarios.find_one({"email": datos.email})
    if not user or not verificar_password(datos.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Correo o contraseña incorrectos")

    user_id = str(user["_id"])
    return {
        "token":   crear_token(user_id),
        "user_id": user_id,
        "name":    f"{user['nombre']} {user['apellidos']}",
        "email":   user["email"],
    }


@router.get("/me")
async def me(user: dict = Depends(usuario_actual)):
    from app.database import db
    rated_count = await db["valoraciones"].count_documents({"user_id": str(user["_id"])})
    watchlist_count = len(user.get("watchlist", []))
    return {
        "id":               str(user["_id"]),
        "name":             f"{user['nombre']} {user['apellidos']}",
        "nombre":           user["nombre"],
        "apellidos":        user["apellidos"],
        "email":            user["email"],
        "created_at":       user.get("created_at"),
        "onboarding_done":  user.get("onboarding_done", False),
        "preferred_groups": user.get("preferred_groups", {}),
        "stats": {
            "rated":     rated_count,
            "watchlist": watchlist_count,
            "liked":     0,
        },
    }


@router.put("/profile")
async def actualizar_perfil(datos: UsuarioDB.Actualizar, user: dict = Depends(usuario_actual)):
    cambios = datos.model_dump(exclude_none=True)
    if not cambios:
        raise HTTPException(status_code=400, detail="No hay nada que actualizar")

    # si cambia el email, comprobar que no lo usa otro usuario
    if "email" in cambios:
        existe = await usuarios.find_one({"email": cambios["email"], "_id": {"$ne": user["_id"]}})
        if existe:
            raise HTTPException(status_code=400, detail="Este correo ya está en uso")

    await usuarios.update_one({"_id": user["_id"]}, {"$set": cambios})
    return {"ok": True}


@router.post("/change-password")
async def cambiar_password(datos: UsuarioDB.CambiarPassword, user: dict = Depends(usuario_actual)):
    if not verificar_password(datos.password_actual, user["password_hash"]):
        raise HTTPException(status_code=400, detail="La contraseña actual no es correcta")

    await usuarios.update_one(
        {"_id": user["_id"]},
        {"$set": {"password_hash": hashear_password(datos.password_nueva)}}
    )
    return {"ok": True}


@router.post("/preferences")
async def guardar_preferencias(datos: UsuarioDB.Preferencias, user: dict = Depends(usuario_actual)):
    await usuarios.update_one(
        {"_id": user["_id"]},
        {"$set": {"preferred_groups": datos.grupos, "onboarding_done": True}}
    )
    return {"ok": True}
