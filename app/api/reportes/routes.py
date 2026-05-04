from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
from typing import Optional

from app.db.database import get_db
from app.models import User, RolEnum, Expediente, Evaluacion, EstadoExpedienteEnum, Dictamen
from app.api.auth.routes import get_current_user

router = APIRouter()

def estado_to_str(estado):
    return estado.value if hasattr(estado, "value") else str(estado)

@router.get("/expedientes-por-estado")
def reportes_expedientes_por_estado(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    resultados = db.query(
        Expediente.estado,
        func.count(Expediente.id).label("total")
    ).group_by(Expediente.estado).all()
    return [{"estado": estado_to_str(r[0]) if r[0] else "sin estado", "total": r[1]} for r in resultados]

@router.get("/tiempos-atencion")
def reportes_tiempos_atencion(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    expedientes = db.query(Expediente).filter(Expediente.fecha_envio != None).all()
    datos = []
    for exp in expedientes:
        if exp.fecha_envio and exp.fecha_creacion:
            dias = (exp.fecha_envio - exp.fecha_creacion).days
            datos.append({"expediente_id": exp.id, "codigo": exp.codigo_unico, "dias": dias, "estado": estado_to_str(exp.estado) if exp.estado else None})
    return datos

@router.get("/carga-evaluadores")
def reportes_carga_evaluadores(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    resultados = db.query(
        Evaluacion.evaluador_id,
        func.count(Evaluacion.id).label("total_evaluaciones")
    ).group_by(Evaluacion.evaluador_id).all()
    return [{"evaluador_id": r[0], "total": r[1]} for r in resultados]

@router.get("/resultados-emitidos")
def reportes_resultados(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    resultados = db.query(
        Dictamen.tipo_dictamen,
        func.count(Dictamen.id).label("total")
    ).group_by(Dictamen.tipo_dictamen).all()
    return [{"tipo": r[0], "total": r[1]} for r in resultados]

@router.get("/buscar-expedientes")
def buscar_expedientes(
    estado: Optional[str] = None,
    fecha_inicio: Optional[str] = None,
    fecha_fin: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(Expediente)
    if estado:
        query = query.filter(Expediente.estado == estado)
    if fecha_inicio:
        query = query.filter(Expediente.fecha_creacion >= datetime.fromisoformat(fecha_inicio))
    if fecha_fin:
        query = query.filter(Expediente.fecha_creacion <= datetime.fromisoformat(fecha_fin))
    return query.all()

@router.get("/exportar")
def exportar_reporte(
    tipo: str = Query(..., description="Tipo de reporte: estados, tiempos, carga, resultados"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.rol not in [RolEnum.ADMINISTRADOR, RolEnum.COORDINADOR, RolEnum.SECRETARIA]:
        raise HTTPException(status_code=403, detail="No tienes acceso")
    return {"message": f"Reporte {tipo} exportado", "formato": "csv"}