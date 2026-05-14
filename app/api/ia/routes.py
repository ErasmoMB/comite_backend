from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional, List, Dict

from app.db.database import get_db
from app.models import User, RolEnum, Expediente, Documento
from app.schemas import IAAnalisisResponse, IAInconsistenciasResponse, IARiesgosResponse
from app.api.auth.routes import get_current_user

router = APIRouter()


def estado_to_str(estado):
    return estado.value if hasattr(estado, "value") else str(estado)

@router.get("/preanalisis/{expediente_id}", response_model=IAAnalisisResponse)
def preanalisis_expediente(expediente_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.rol not in [RolEnum.ADMINISTRADOR, RolEnum.COORDINADOR, RolEnum.SECRETARIA, RolEnum.EVALUADOR]:
        raise HTTPException(status_code=403, detail="No tienes acceso")
    exp = db.query(Expediente).filter(Expediente.id == expediente_id).first()
    if not exp:
        raise HTTPException(status_code=404, detail="Expediente no encontrado")
    return IAAnalisisResponse(
        analisis=f"Análisis preliminar del protocolo: {exp.titulo_protocolo}. Tipo: {exp.tipo_tramite}. Facultad: {exp.facultad}",
        nivel_riesgo="medio",
        recomendaciones=[
            "Requiere integración con modelo de IA (OpenAI, Claude, etc.)",
            "Análisis semántico del protocolo",
            "Detección de patrones éticos"
        ],
        confianza=0.0,
        factores_clave=["Revisión pendiente", "Análisis de contenido"]
    )

@router.get("/detectar-inconsistencias/{expediente_id}", response_model=IAInconsistenciasResponse)
def detectar_inconsistencias(expediente_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.rol not in [RolEnum.EVALUADOR, RolEnum.COORDINADOR, RolEnum.SECRETARIA]:
        raise HTTPException(status_code=403, detail="No tienes acceso")
    exp = db.query(Expediente).filter(Expediente.id == expediente_id).first()
    if not exp:
        raise HTTPException(status_code=404, detail="Expediente no encontrado")
    return IAInconsistenciasResponse(
        inconsistencias=[],
        cantidad=0,
        mensaje="Requiere integración con modelo de IA para análisis de contenido"
    )

@router.get("/detectar-riesgos/{expediente_id}", response_model=IARiesgosResponse)
def detectar_riesgos_eticos(expediente_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.rol not in [RolEnum.EVALUADOR, RolEnum.COORDINADOR, RolEnum.SECRETARIA]:
        raise HTTPException(status_code=403, detail="No tienes acceso")
    exp = db.query(Expediente).filter(Expediente.id == expediente_id).first()
    if not exp:
        raise HTTPException(status_code=404, detail="Expediente no encontrado")
    return IARiesgosResponse(
        nivel_riesgo="pendiente_analisis",
        factores=[],
        recomendaciones=["Requiere integración con modelo de IA para evaluación de riesgos éticos"],
        mensaje="Análisis pendiente"
    )

@router.get("/generar-observaciones/{expediente_id}")
def generar_observaciones_sugeridas(expediente_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.rol != RolEnum.EVALUADOR:
        raise HTTPException(status_code=403, detail="Solo evaluadores")
    exp = db.query(Expediente).filter(Expediente.id == expediente_id).first()
    if not exp:
        raise HTTPException(status_code=404, detail="Expediente no encontrado")
    return {
        "observaciones_sugeridas": [],
        "mensaje": "Requiere integración con modelo de IA para generación de observaciones",
        "expediente_id": expediente_id
    }

@router.get("/resumen/{expediente_id}")
def generar_resumen_expediente(expediente_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    exp = db.query(Expediente).filter(Expediente.id == expediente_id).first()
    if not exp:
        raise HTTPException(status_code=404, detail="Expediente no encontrado")
    documentos = db.query(Documento).filter(Documento.expediente_id == expediente_id).all()
    return {
        "expediente_id": expediente_id,
        "titulo": exp.titulo_protocolo,
        "estado": estado_to_str(exp.estado) if exp.estado else None,
        "documentos_count": len(documentos),
        "resumen": "Resumen generado por IA - Requiere integración con modelo LLM"
    }