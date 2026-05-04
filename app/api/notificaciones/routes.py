from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.db.database import get_db
from app.models import User, Notificacion
from app.schemas import NotificacionCreate, NotificacionResponse, NotificacionUpdate
from app.api.auth.routes import get_current_user

router = APIRouter()

@router.get("/", response_model=List[NotificacionResponse])
def get_notificaciones(skip: int = 0, limit: int = 50, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(Notificacion).filter(Notificacion.usuario_id == current_user.id).order_by(Notificacion.created_at.desc()).offset(skip).limit(limit).all()

@router.get("/sin-leer")
def count_no_leidas(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    count = db.query(Notificacion).filter(Notificacion.usuario_id == current_user.id, Notificacion.leida == False).count()
    return {"sin_leer": count}

@router.get("/{notificacion_id}", response_model=NotificacionResponse)
def get_notificacion(notificacion_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    notif = db.query(Notificacion).filter(Notificacion.id == notificacion_id, Notificacion.usuario_id == current_user.id).first()
    if not notif:
        raise HTTPException(status_code=404, detail="Notificación no encontrada")
    return notif

@router.post("/", response_model=NotificacionResponse)
def create_notificacion(notif: NotificacionCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    nueva = Notificacion(
        usuario_id=notif.usuario_id,
        titulo=notif.titulo,
        mensaje=notif.mensaje,
        expediente_id=notif.expediente_id
    )
    db.add(nueva)
    db.commit()
    db.refresh(nueva)
    return nueva

@router.put("/{notificacion_id}", response_model=NotificacionResponse)
def update_notificacion(notificacion_id: int, notif_update: NotificacionUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    notif = db.query(Notificacion).filter(Notificacion.id == notificacion_id, Notificacion.usuario_id == current_user.id).first()
    if not notif:
        raise HTTPException(status_code=404, detail="Notificación no encontrada")
    if notif_update.leida is not None:
        notif.leida = notif_update.leida
    db.commit()
    db.refresh(notif)
    return notif

@router.post("/marcar-todas-leidas")
def marcar_todas_leidas(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    db.query(Notificacion).filter(Notificacion.usuario_id == current_user.id, Notificacion.leida == False).update({"leida": True})
    db.commit()
    return {"message": "Todas las notificaciones marcadas como leídas"}

def crear_notificacion(db, usuario_id, titulo, mensaje, expediente_id=None):
    notif = Notificacion(usuario_id=usuario_id, titulo=titulo, mensaje=mensaje, expediente_id=expediente_id)
    db.add(notif)
    return notif