from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
from typing import Optional, List

from app.db.database import get_db
from app.models import User, RolEnum, Expediente, Evaluacion, EstadoExpedienteEnum, Dictamen
from app.schemas import ReporteTiempoAtencion, ReporteCargaEvaluadores, ReporteResultados, ReporteGeneralResponse, EstadisticasExpediente, EstadisticasEvaluadores
from app.api.auth.routes import get_current_user

router = APIRouter()

def estado_to_str(estado):
    return estado.value if hasattr(estado, "value") else str(estado)

@router.get("/expedientes-por-estado", response_model=EstadisticasExpediente)
def reportes_expedientes_por_estado(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    total = db.query(func.count(Expediente.id)).scalar()
    resultados = db.query(
        Expediente.estado,
        func.count(Expediente.id).label("total")
    ).group_by(Expediente.estado).all()
    por_estado = {estado_to_str(r[0]) if r[0] else "sin estado": r[1] for r in resultados}
    return EstadisticasExpediente(total=total, por_estado=por_estado)

@router.get("/tiempos-atencion", response_model=List[ReporteTiempoAtencion])
def reportes_tiempos_atencion(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    expedientes = db.query(Expediente).filter(Expediente.fecha_envio != None).all()
    datos = []
    for exp in expedientes:
        if exp.fecha_envio and exp.fecha_creacion:
            dias = (exp.fecha_envio - exp.fecha_creacion).days
            datos.append(ReporteTiempoAtencion(
                expediente_id=exp.id, 
                codigo=exp.codigo_unico, 
                dias=dias, 
                estado=estado_to_str(exp.estado) if exp.estado else "desconocido"
            ))
    return datos

@router.get("/carga-evaluadores", response_model=List[ReporteCargaEvaluadores])
def reportes_carga_evaluadores(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    try:
        resultados = db.query(
            Evaluacion.evaluador_id,
            func.count(Evaluacion.id).label("total_evaluaciones")
        ).group_by(Evaluacion.evaluador_id).all()
        
        datos = []
        for evaluador_id, total in resultados:
            # Obtener nombre del evaluador por separado
            evaluador = db.query(User).filter(User.id == evaluador_id).first()
            datos.append(ReporteCargaEvaluadores(
                evaluador_id=evaluador_id,
                nombre=evaluador.nombres if evaluador else None,
                total_evaluaciones=total
            ))
        return datos
    except Exception as e:
        print(f"Error en carga_evaluadores: {str(e)}")
        return []

@router.get("/resultados-emitidos", response_model=List[ReporteResultados])
def reportes_resultados(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Reporta los dictamenes emitidos agrupados por tipo.
    
    **Solo retorna:** aprobado, observado (sin desaprobado/rechazado)
    """
    resultados = db.query(
        Dictamen.tipo_dictamen,
        func.count(Dictamen.id).label("total")
    ).filter(
        Dictamen.tipo_dictamen.in_(["aprobado", "observado"])
    ).group_by(Dictamen.tipo_dictamen).all()
    
    datos = []
    for r in resultados:
        tipo = r[0] if r[0] else "sin tipo"
        # Filtrar tipos inválidos adicionales por si acaso
        if tipo.lower() not in ["aprobado", "observado"]:
            continue
        datos.append(ReporteResultados(
            tipo=tipo,
            total=r[1]
        ))
    return datos

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

@router.get("/resumen", response_model=ReporteGeneralResponse)
def resumen_general(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Genera un reporte general completo del sistema"""
    if current_user.rol not in [RolEnum.ADMINISTRADOR, RolEnum.COORDINADOR, RolEnum.SECRETARIA]:
        raise HTTPException(status_code=403, detail="No tienes acceso a reportes")
    
    try:
        # Estadísticas de expedientes
        total_expedientes = db.query(func.count(Expediente.id)).scalar() or 0
        por_estado_query = db.query(
            Expediente.estado,
            func.count(Expediente.id).label("total")
        ).group_by(Expediente.estado).all()
        por_estado = {estado_to_str(r[0]) if r[0] else "sin estado": r[1] for r in por_estado_query}
        
        # Estadísticas de evaluadores
        total_evaluadores = db.query(func.count(User.id)).filter(User.rol == RolEnum.EVALUADOR).scalar() or 0
        
        # Carga promedio y máxima (calculadas manualmente)
        carga_por_evaluador = db.query(
            Evaluacion.evaluador_id,
            func.count(Evaluacion.id).label("total")
        ).group_by(Evaluacion.evaluador_id).all()
        
        cargas = [total for _, total in carga_por_evaluador]
        carga_promedio = sum(cargas) / len(cargas) if cargas else 0.0
        carga_maxima = max(cargas) if cargas else 0
        
        # Tiempos de atención
        tiempos = []
        expedientes_enviados = db.query(Expediente).filter(Expediente.fecha_envio != None).all()
        for exp in expedientes_enviados:
            if exp.fecha_envio and exp.fecha_creacion:
                dias = (exp.fecha_envio - exp.fecha_creacion).days
                tiempos.append(ReporteTiempoAtencion(
                    expediente_id=exp.id,
                    codigo=exp.codigo_unico,
                    dias=dias,
                    estado=estado_to_str(exp.estado) if exp.estado else "desconocido"
                ))
        
        # Carga de evaluadores
        carga_evaluadores = []
        for evaluador_id, total in carga_por_evaluador:
            evaluador = db.query(User).filter(User.id == evaluador_id).first()
            carga_evaluadores.append(ReporteCargaEvaluadores(
                evaluador_id=evaluador_id,
                nombre=evaluador.nombres if evaluador else None,
                total_evaluaciones=total
            ))
        
        # Resultados emitidos
        resultados_query = db.query(
            Dictamen.tipo_dictamen,
            func.count(Dictamen.id).label("total")
        ).group_by(Dictamen.tipo_dictamen).all()
        
        resultados = []
        for tipo, total in resultados_query:
            resultados.append(ReporteResultados(
                tipo=tipo if tipo else "sin tipo",
                total=total
            ))
        
        return ReporteGeneralResponse(
            fecha_generacion=datetime.utcnow(),
            expedientes=EstadisticasExpediente(total=total_expedientes, por_estado=por_estado),
            evaluadores=EstadisticasEvaluadores(
                total_evaluadores=total_evaluadores,
                carga_promedio=carga_promedio,
                carga_maxima=carga_maxima
            ),
            tiempos_atencion=tiempos,
            carga_evaluadores=carga_evaluadores,
            resultados=resultados
        )
    except Exception as e:
        print(f"Error en resumen_general: {str(e)}")
        # Retornar un reporte vacío para evitar error 500
        return ReporteGeneralResponse(
            fecha_generacion=datetime.utcnow(),
            expedientes=EstadisticasExpediente(total=0, por_estado={}),
            evaluadores=EstadisticasEvaluadores(total_evaluadores=0, carga_promedio=0.0, carga_maxima=0),
            tiempos_atencion=[],
            carga_evaluadores=[],
            resultados=[]
        )

@router.get("/exportar")
def exportar_reporte(
    tipo: str = Query(..., description="Tipo de reporte: estados, tiempos, carga, resultados"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.rol not in [RolEnum.ADMINISTRADOR, RolEnum.COORDINADOR, RolEnum.SECRETARIA]:
        raise HTTPException(status_code=403, detail="No tienes acceso")
    return {"message": f"Reporte {tipo} exportado", "formato": "csv"}