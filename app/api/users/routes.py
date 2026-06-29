from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.db.database import get_db
from app.core.security import get_password_hash
from app.models import User, RolEnum
from app.schemas import UserResponse, UserUpdate, AdminUserCreate
from app.api.auth.routes import get_current_user

router = APIRouter()


@router.post("/", response_model=UserResponse, status_code=201)
def create_user(
    payload: AdminUserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Solo el administrador puede crear usuarios (incluidos los roles internos)."""
    if current_user.rol != RolEnum.ADMINISTRADOR.value:
        raise HTTPException(
            status_code=403,
            detail="Solo el administrador puede crear usuarios.",
        )

    roles_validos = {r.value for r in RolEnum}
    if payload.rol not in roles_validos:
        raise HTTPException(status_code=400, detail="Rol no válido.")

    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=400, detail="Email ya registrado")

    new_user = User(
        email=payload.email,
        password_hash=get_password_hash(payload.password),
        nombre=payload.nombre,
        apellido=payload.apellido,
        rol=payload.rol,
        especialidad=payload.especialidad,
        carga_trabajo=payload.carga_trabajo,
        conflicto_interes=payload.conflicto_interes,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@router.get("/", response_model=List[UserResponse])
def get_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    users = db.query(User).offset(skip).limit(limit).all()
    return users

@router.get("/me", response_model=UserResponse)
def get_current_user_info(current_user: User = Depends(get_current_user)):
    return current_user

@router.get("/{user_id}", response_model=UserResponse)
def get_user(user_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return user

@router.put("/{user_id}", response_model=UserResponse)
def update_user(user_id: int, user_update: UserUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.rol != RolEnum.ADMINISTRADOR and current_user.id != user_id:
        raise HTTPException(status_code=403, detail="No tienes permisos")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    if user_update.nombre:
        user.nombre = user_update.nombre
    if user_update.apellido:
        user.apellido = user_update.apellido
    if user_update.rol and current_user.rol == RolEnum.ADMINISTRADOR:
        user.rol = user_update.rol
    if user_update.activo is not None and current_user.rol == RolEnum.ADMINISTRADOR:
        user.activo = user_update.activo
    db.commit()
    db.refresh(user)
    return user

@router.delete("/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.rol != RolEnum.ADMINISTRADOR:
        raise HTTPException(status_code=403, detail="Solo administradores pueden eliminar usuarios")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    user.activo = False
    db.commit()
    return {"message": "Usuario desactivado"}