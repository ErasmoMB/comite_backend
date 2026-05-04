from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
import uuid

from app.db.database import get_db
from app.models import User, RolEnum, Expediente, Dictamen, Evaluacion
from app.schemas import DictamenCreate, DictamenResponse, DictamenUpdate
from app.api.auth.routes import get_current_user

router = APIRouter()

def generar_numero_dictamen():
    año = datetime.now().year
    return f"DICT-{año}-{uuid.uuid4().hex[:6].upper()}"

@router.get("/", response_model=List[DictamenResponse])
def get_dictamines(skip: int = 0, limit: int = 50, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(Dictamen).offset(skip).limit(limit).all()

@router.get("/{dictamen_id}", response_model=DictamenResponse)
def get_dictamen(dictamen_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    dictamen = db.query(Dictamen).filter(Dictamen.id == dictamen_id).first()
    if not dictamen:
        raise HTTPException(status_code=404, detail="Dictamen no encontrado")
    return dictamen

@router.get("/expediente/{expediente_id}", response_model=List[DictamenResponse])
def get_dictamenes_by_expediente(expediente_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(Dictamen).filter(Dictamen.expediente_id == expediente_id).all()

@router.post("/", response_model=DictamenResponse)
def create_dictamen(dictamen: DictamenCreate, tipo_dictamen: str = "aprobado", db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.rol not in [RolEnum.ADMINISTRADOR, RolEnum.COORDINADOR]:
        raise HTTPException(status_code=403, detail="Solo coordinadores pueden generar dictámenes")
    exp = db.query(Expediente).filter(Expediente.id == dictamen.expediente_id).first()
    if not exp:
        raise HTTPException(status_code=404, detail="Expediente no encontrado")
    evaluaciones = db.query(Evaluacion).filter(Evaluacion.expediente_id == dictamen.expediente_id, Evaluacion.completa == True).all()
    if len(evaluaciones) < 2:
        raise HTTPException(status_code=400, detail="Se necesitan al menos 2 evaluaciones completas para generar dictamen")
    nuevo_dictamen = Dictamen(
        expediente_id=dictamen.expediente_id,
        contenido=dictamen.contenido,
        tipo_dictamen=tipo_dictamen,
        numero_dictamen=generar_numero_dictamen(),
        fecha_emision=datetime.utcnow()
    )
    db.add(nuevo_dictamen)
    db.commit()
    db.refresh(nuevo_dictamen)
    return nuevo_dictamen

@router.put("/{dictamen_id}", response_model=DictamenResponse)
def update_dictamen(dictamen_id: int, dict_update: DictamenUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    dictamen = db.query(Dictamen).filter(Dictamen.id == dictamen_id).first()
    if not dictamen:
        raise HTTPException(status_code=404, detail="Dictamen no encontrado")
    if current_user.rol not in [RolEnum.ADMINISTRADOR, RolEnum.COORDINADOR]:
        raise HTTPException(status_code=403, detail="No tienes permisos")
    if dict_update.contenido:
        dictamen.contenido = dict_update.contenido
    if dict_update.firmado is not None:
        dictamen.firmado = dict_update.firmado
    db.commit()
    db.refresh(dictamen)
    return dictamen

@router.post("/{dictamen_id}/firmar")
def firmar_dictamen(dictamen_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.rol not in [RolEnum.COORDINADOR, RolEnum.ADMINISTRADOR]:
        raise HTTPException(status_code=403, detail="Solo coordinadores pueden firmar")
    dictamen = db.query(Dictamen).filter(Dictamen.id == dictamen_id).first()
    if not dictamen:
        raise HTTPException(status_code=404, detail="Dictamen no encontrado")
    if not dictamen.contenido:
        raise HTTPException(status_code=400, detail="El dictamen no tiene contenido")
    dictamen.firmado = True
    db.commit()
    return {"message": "Dictamen firmado exitosamente", "numero": dictamen.numero_dictamen}