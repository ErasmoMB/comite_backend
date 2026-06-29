"""Configuración global del sistema (fecha límite de envío, etc.)."""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models import User, RolEnum, Configuracion
from app.api.auth.routes import get_current_user

router = APIRouter()

CLAVE_FECHA_LIMITE = "fecha_limite_envio"


class FechaLimiteIn(BaseModel):
    fecha_limite: Optional[str] = None  # ISO 8601 (UTC) o null para quitarla


def leer_config(db: Session, clave: str) -> Optional[str]:
    fila = db.query(Configuracion).filter(Configuracion.clave == clave).first()
    return fila.valor if fila else None


def guardar_config(db: Session, clave: str, valor: Optional[str]):
    fila = db.query(Configuracion).filter(Configuracion.clave == clave).first()
    if fila:
        fila.valor = valor
    else:
        db.add(Configuracion(clave=clave, valor=valor))
    db.commit()


@router.get("/fecha-limite")
def get_fecha_limite(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return {"fecha_limite": leer_config(db, CLAVE_FECHA_LIMITE)}


@router.put("/fecha-limite")
def set_fecha_limite(
    payload: FechaLimiteIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.rol != RolEnum.ADMINISTRADOR.value:
        raise HTTPException(status_code=403, detail="Solo el administrador puede configurar la fecha límite.")

    valor = None
    if payload.fecha_limite:
        try:
            datetime.fromisoformat(payload.fecha_limite.replace("Z", "+00:00"))
        except ValueError:
            raise HTTPException(status_code=400, detail="Fecha inválida.")
        valor = payload.fecha_limite

    guardar_config(db, CLAVE_FECHA_LIMITE, valor)
    return {"fecha_limite": valor}
