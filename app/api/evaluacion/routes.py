from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime

from app.db.database import get_db
from app.models import User, RolEnum, Expediente, Evaluacion, EstadoExpedienteEnum, Notificacion
from app.schemas import EvaluacionCreate, EvaluacionResponse, EvaluacionUpdate
from app.api.auth.routes import get_current_user

router = APIRouter()

@router.get("/", response_model=List[EvaluacionResponse])
def get_evaluaciones(skip: int = 0, limit: int = 50, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.rol == RolEnum.EVALUADOR:
        return db.query(Evaluacion).filter(Evaluacion.evaluador_id == current_user.id).offset(skip).limit(limit).all()
    return db.query(Evaluacion).offset(skip).limit(limit).all()

@router.get("/mis-evaluaciones", response_model=List[EvaluacionResponse])
def get_my_evaluaciones(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.rol != RolEnum.EVALUADOR:
        raise HTTPException(status_code=403, detail="Solo evaluadores")
    return db.query(Evaluacion).filter(Evaluacion.evaluador_id == current_user.id).all()

@router.get("/{evaluacion_id}", response_model=EvaluacionResponse)
def get_evaluacion(evaluacion_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    evaluacion = db.query(Evaluacion).filter(Evaluacion.id == evaluacion_id).first()
    if not evaluacion:
        raise HTTPException(status_code=404, detail="Evaluación no encontrada")
    return evaluacion

@router.post("/", response_model=EvaluacionResponse)
def create_evaluacion(evaluacion: EvaluacionCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.rol not in [RolEnum.ADMINISTRADOR, RolEnum.COORDINADOR]:
        raise HTTPException(status_code=403, detail="Solo coordinadores pueden crear evaluaciones")
    exp = db.query(Expediente).filter(Expediente.id == evaluacion.expediente_id).first()
    if not exp:
        raise HTTPException(status_code=404, detalle="Expediente no encontrado")
    existentes = db.query(Evaluacion).filter(Evaluacion.expediente_id == evaluacion.expediente_id).all()
    if len(existentes) >= 2:
        raise HTTPException(status_code=400, detail="Ya hay 2 evaluadores asignados")
    nueva_eval = Evaluacion(expediente_id=evaluacion.expediente_id, evaluador_id=current_user.id)
    db.add(nueva_eval)
    db.commit()
    db.refresh(nueva_eval)
    return nueva_eval

@router.put("/{evaluacion_id}", response_model=EvaluacionResponse)
def update_evaluacion(evaluacion_id: int, eval_update: EvaluacionUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    evaluacion = db.query(Evaluacion).filter(Evaluacion.id == evaluacion_id).first()
    if not evaluacion:
        raise HTTPException(status_code=404, detail="Evaluación no encontrada")
    if evaluacion.evaluador_id != current_user.id and current_user.rol != RolEnum.ADMINISTRADOR:
        raise HTTPException(status_code=403, detail="No puedes modificar esta evaluación")
    if eval_update.nivel_riesgo is not None:
        evaluacion.nivel_riesgo = eval_update.nivel_riesgo
    if eval_update.recommendation is not None:
        evaluacion.recommendation = eval_update.recommendation
    if eval_update.observaciones is not None:
        evaluacion.observaciones = eval_update.observaciones
    if eval_update.completa is not None:
        evaluacion.completa = eval_update.completa
        if eval_update.completa:
            evaluacion.fecha_envio = datetime.utcnow()
    db.commit()
    db.refresh(evaluacion)
    return evaluacion

@router.post("/{evaluacion_id}/conflicto")
def declarar_conflicto(evaluacion_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    evaluacion = db.query(Evaluacion).filter(Evaluacion.id == evaluacion_id).first()
    if not evaluacion:
        raise HTTPException(status_code=404, detail="Evaluación no encontrada")
    if evaluacion.evaluador_id != current_user.id:
        raise HTTPException(status_code=403, detail="No puedes declarar conflicto por otro evaluador")
    evaluacion.conflicto_interes = True
    db.commit()
    return {"message": "Conflicto de interés declarado"}

@router.post("/{evaluacion_id}/guardar-parcial")
def guardar_parcial(evaluacion_id: int, eval_update: EvaluacionUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    evaluacion = db.query(Evaluacion).filter(Evaluacion.id == evaluacion_id).first()
    if not evaluacion:
        raise HTTPException(status_code=404, detail="Evaluación no encontrada")
    if evaluacion.evaluador_id != current_user.id:
        raise HTTPException(status_code=403, detail="No tienes acceso")
    if eval_update.observaciones is not None:
        evaluacion.observaciones = eval_update.observaciones
    if eval_update.nivel_riesgo is not None:
        evaluacion.nivel_riesgo = eval_update.nivel_riesgo
    db.commit()
    return {"message": "Guardado parcial exitoso"}