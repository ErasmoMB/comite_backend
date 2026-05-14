from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
import uuid

from app.db.database import get_db
from app.models import User, RolEnum, EstadoExpedienteEnum, Expediente, Documento, Bitacora, HistorialExpediente
from app.schemas import ExpedienteCreate, ExpedienteResponse, ExpedienteUpdate, DocumentoResponse, SubsanacionResponse
from app.api.auth.routes import get_current_user

router = APIRouter()

def generar_codigo():
    return f"CE-{uuid.uuid4().hex[:8].upper()}"

def registrar_bitacora(db, expediente_id, accion, detalle=None, usuario_id=None):
    bitacora = Bitacora(expediente_id=expediente_id, accion=accion, detalle=detalle, usuario_id=usuario_id)
    db.add(bitacora)

def actualizar_estado(db, expediente, nuevo_estado, observaciones=None):
    estado_anterior = expediente.estado.value if hasattr(expediente.estado, "value") else expediente.estado
    estado_nuevo = nuevo_estado.value if hasattr(nuevo_estado, "value") else nuevo_estado
    historial = HistorialExpediente(
        expediente_id=expediente.id,
        estado_anterior=estado_anterior,
        estado_nuevo=estado_nuevo,
        observaciones=observaciones
    )
    db.add(historial)
    expediente.estado = estado_nuevo

@router.get("/", response_model=List[ExpedienteResponse])
def get_expedientes(skip: int = 0, limit: int = 50, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.rol in [RolEnum.ADMINISTRADOR, RolEnum.COORDINADOR, RolEnum.SECRETARIA]:
        return db.query(Expediente).offset(skip).limit(limit).all()
    return db.query(Expediente).filter(Expediente.investigador_id == current_user.id).offset(skip).limit(limit).all()

@router.get("/{expediente_id}", response_model=ExpedienteResponse)
def get_expediente(expediente_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    exp = db.query(Expediente).filter(Expediente.id == expediente_id).first()
    if not exp:
        raise HTTPException(status_code=404, detail="Expediente no encontrado")
    if current_user.rol == RolEnum.INVESTIGADOR and exp.investigador_id != current_user.id:
        raise HTTPException(status_code=403, detail="No tienes acceso a este expediente")
    return exp

@router.post("/", response_model=ExpedienteResponse)
def create_expediente(expediente: ExpedienteCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    new_exp = Expediente(
        titulo_protocolo=expediente.titulo_protocolo,
        tipo_tramite=expediente.tipo_tramite,
        facultad=expediente.facultad,
        prioridad=expediente.prioridad or "normal",
        investigador_id=current_user.id,
        estado=EstadoExpedienteEnum.BORRADOR,
        codigo_unico=generar_codigo()
    )
    db.add(new_exp)
    db.commit()
    db.refresh(new_exp)
    registrar_bitacora(db, new_exp.id, "Expediente creado", f"Título: {expediente.titulo_protocolo}", current_user.id)
    db.commit()
    return new_exp

@router.put("/{expediente_id}", response_model=ExpedienteResponse)
def update_expediente(expediente_id: int, exp_update: ExpedienteUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    exp = db.query(Expediente).filter(Expediente.id == expediente_id).first()
    if not exp:
        raise HTTPException(status_code=404, detail="Expediente no encontrado")
    if exp.estado != EstadoExpedienteEnum.BORRADOR and current_user.rol == RolEnum.INVESTIGADOR:
        raise HTTPException(status_code=403, detail="No puedes modificar un expediente enviado")
    if exp_update.titulo_protocolo:
        exp.titulo_protocolo = exp_update.titulo_protocolo
    if exp_update.tipo_tramite is not None:
        exp.tipo_tramite = exp_update.tipo_tramite
    if exp_update.facultad is not None:
        exp.facultad = exp_update.facultad
    if exp_update.prioridad is not None:
        exp.prioridad = exp_update.prioridad
    if exp_update.estado:
        actualizar_estado(db, exp, exp_update.estado)
        registrar_bitacora(db, exp.id, f"Estado cambiado a {exp_update.estado}", None, current_user.id)
    db.commit()
    db.refresh(exp)
    return exp

@router.post("/{expediente_id}/enviar")
def enviar_expediente(expediente_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    exp = db.query(Expediente).filter(Expediente.id == expediente_id).first()
    if not exp:
        raise HTTPException(status_code=404, detail="Expediente no encontrado")
    if exp.investigador_id != current_user.id:
        raise HTTPException(status_code=403, detail="No tienes acceso")
    if exp.estado != EstadoExpedienteEnum.BORRADOR:
        raise HTTPException(status_code=400, detail="El expediente ya fue enviado")
    actualizar_estado(db, exp, EstadoExpedienteEnum.ENVIADO)
    exp.fecha_envio = datetime.utcnow()
    registrar_bitacora(db, exp.id, "Expediente enviado formalmente", None, current_user.id)
    db.commit()
    return {"message": "Expediente enviado exitosamente", "codigo": exp.codigo_unico}

@router.get("/{expediente_id}/bitacora")
def get_bitacora(expediente_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    bitacoras = db.query(Bitacora).filter(Bitacora.expediente_id == expediente_id).order_by(Bitacora.created_at.desc()).all()
    return [{"id": b.id, "accion": b.accion, "detalle": b.detalle, "created_at": b.created_at} for b in bitacoras]

@router.get("/{expediente_id}/historial")
def get_historial(expediente_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    historial = db.query(HistorialExpediente).filter(HistorialExpediente.expediente_id == expediente_id).order_by(HistorialExpediente.created_at.desc()).all()
    return historial

@router.post("/{expediente_id}/documentos", response_model=DocumentoResponse)
async def upload_documento(
    expediente_id: int, 
    file: UploadFile = File(...), 
    tipo_documento: str = "documento",
    es_obligatorio: bool = True,
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    # Validaciones
    TIPOS_PERMITIDOS = {"application/pdf", "application/msword", 
                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        "application/vnd.ms-excel",
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        "text/plain"}
    EXTENSIONES_PERMITIDAS = {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".txt"}
    TAMAÑO_MAXIMO = 10 * 1024 * 1024  # 10 MB
    
    # Validar MIME type
    if file.content_type not in TIPOS_PERMITIDOS:
        raise HTTPException(
            status_code=400, 
            detail=f"Tipo de archivo no permitido. Permitidos: PDF, DOC, DOCX, XLS, XLSX, TXT"
        )
    
    # Validar extensión
    from pathlib import Path as PathlibPath
    file_ext = PathlibPath(file.filename).suffix.lower()
    if file_ext not in EXTENSIONES_PERMITIDAS:
        raise HTTPException(
            status_code=400, 
            detail=f"Extensión no permitida: {file_ext}. Permitidas: {', '.join(EXTENSIONES_PERMITIDAS)}"
        )
    
    # Validar tamaño
    contenido = await file.read()
    if len(contenido) > TAMAÑO_MAXIMO:
        raise HTTPException(
            status_code=400, 
            detail=f"Archivo muy grande. Máximo permitido: 10 MB, tamaño del archivo: {len(contenido) / (1024*1024):.2f} MB"
        )
    
    exp = db.query(Expediente).filter(Expediente.id == expediente_id).first()
    if not exp:
        raise HTTPException(status_code=404, detail="Expediente no encontrado")
    if exp.estado not in [EstadoExpedienteEnum.BORRADOR, EstadoExpedienteEnum.SUBSANACION]:
        raise HTTPException(status_code=400, detail="No puedes agregar documentos en este estado")
    
    # Guardar archivo con nombre único
    import os
    from pathlib import Path
    import uuid
    
    upload_dir = Path("uploads") / str(expediente_id)
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    # Generar nombre único para evitar conflictos
    nombre_base = PathlibPath(file.filename).stem
    extension = PathlibPath(file.filename).suffix
    nombre_unico = f"{nombre_base}_{uuid.uuid4().hex[:8]}{extension}"
    
    file_path = upload_dir / nombre_unico
    with open(file_path, "wb") as buffer:
        buffer.write(contenido)
    
    doc = Documento(
        expediente_id=expediente_id, 
        nombre_archivo=file.filename, 
        tipo_documento=tipo_documento, 
        es_obligatorio=es_obligatorio,
        ruta_archivo=str(file_path)
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    registrar_bitacora(db, expediente_id, "Documento subido", 
                      f"Archivo: {file.filename} (MIME: {file.content_type}, Tamaño: {len(contenido)} bytes)", 
                      current_user.id)
    db.commit()
    return doc


@router.post("/{expediente_id}/subsanacion", response_model=SubsanacionResponse)
async def submit_subsanacion(
    expediente_id: int,
    observaciones: str = "",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Registra la respuesta de subsanación del investigador.
    El investigador responde a las observaciones de evaluadores.
    """
    exp = db.query(Expediente).filter(Expediente.id == expediente_id).first()
    if not exp:
        raise HTTPException(status_code=404, detail="Expediente no encontrado")
    
    if exp.estado != EstadoExpedienteEnum.SUBSANACION:
        raise HTTPException(
            status_code=400, 
            detail=f"El expediente debe estar en estado SUBSANACION. Estado actual: {exp.estado}"
        )
    
    # Registrar subsanación en bitácora
    registrar_bitacora(
        db, 
        expediente_id, 
        "Subsanación respondida", 
        f"Observaciones: {observaciones[:200]}...",
        current_user.id
    )
    
    # No cambiar estado aquí - solo registrar respuesta
    # El estado cambiará cuando coordinador decida re-evaluar
    
    db.commit()
    
    return SubsanacionResponse(
        mensaje="Subsanación registrada correctamente. Pendiente de revisión coordinada.",
        expediente_id=expediente_id,
        estado=exp.estado,
        fecha_subsanacion=datetime.utcnow()
    )