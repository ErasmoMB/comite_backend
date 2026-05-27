from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
import uuid
from pathlib import Path

from app.db.database import get_db
from app.models import User, RolEnum, Expediente, Dictamen, Evaluacion
from app.schemas import DictamenCreate, DictamenResponse, DictamenUpdate
from app.api.auth.routes import get_current_user
from app.utils.pdf_generator import generar_pdf_dictamen

router = APIRouter()

TIPOS_DICTAMEN_VALIDOS = ["aprobado", "observado"]

def generar_numero_dictamen():
    año = datetime.now().year
    return f"DICT-{año}-{uuid.uuid4().hex[:6].upper()}"

def validar_tipo_dictamen(tipo: str) -> bool:
    """Valida que tipo_dictamen sea aprobado u observado"""
    return tipo.lower() in TIPOS_DICTAMEN_VALIDOS

@router.get("/", response_model=List[DictamenResponse])
def get_dictamines(skip: int = 0, limit: int = 50, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Lista todos los dictamenes"""
    return db.query(Dictamen).offset(skip).limit(limit).all()

@router.get("/{dictamen_id}", response_model=DictamenResponse)
def get_dictamen(dictamen_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Obtiene un dictamen por ID"""
    dictamen = db.query(Dictamen).filter(Dictamen.id == dictamen_id).first()
    if not dictamen:
        raise HTTPException(status_code=404, detail="Dictamen no encontrado")
    return dictamen

@router.get("/expediente/{expediente_id}", response_model=List[DictamenResponse])
def get_dictamenes_by_expediente(expediente_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Obtiene todos los dictamenes de un expediente"""
    return db.query(Dictamen).filter(Dictamen.expediente_id == expediente_id).all()

@router.post("/", response_model=DictamenResponse)
def create_dictamen(
    dictamen: DictamenCreate, 
    tipo_dictamen: str = "aprobado", 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    """
    Crea un nuevo dictamen.
    
    **Validaciones:**
    - Solo coordinadores/administradores
    - tipo_dictamen: SOLO "aprobado" o "observado" (no rechazado)
    - Mínimo 2 evaluaciones completas
    """
    if current_user.rol not in [RolEnum.ADMINISTRADOR, RolEnum.COORDINADOR]:
        raise HTTPException(status_code=403, detail="Solo coordinadores pueden generar dictámenes")
    
    # Validar tipo de dictamen
    if not validar_tipo_dictamen(tipo_dictamen):
        raise HTTPException(
            status_code=400, 
            detail=f"tipo_dictamen inválido. Permitidos: {', '.join(TIPOS_DICTAMEN_VALIDOS)}"
        )
    
    exp = db.query(Expediente).filter(Expediente.id == dictamen.expediente_id).first()
    if not exp:
        raise HTTPException(status_code=404, detail="Expediente no encontrado")
    
    evaluaciones = db.query(Evaluacion).filter(
        Evaluacion.expediente_id == dictamen.expediente_id, 
        Evaluacion.completa == True
    ).all()
    
    if len(evaluaciones) < 2:
        raise HTTPException(status_code=400, detail="Se necesitan al menos 2 evaluaciones completas para generar dictamen")
    
    nuevo_dictamen = Dictamen(
        expediente_id=dictamen.expediente_id,
        contenido=dictamen.contenido,
        tipo_dictamen=tipo_dictamen.lower(),
        numero_dictamen=generar_numero_dictamen(),
        fecha_emision=datetime.utcnow()
    )
    db.add(nuevo_dictamen)
    db.commit()
    db.refresh(nuevo_dictamen)
    return nuevo_dictamen

@router.put("/{dictamen_id}", response_model=DictamenResponse)
def update_dictamen(
    dictamen_id: int, 
    dict_update: DictamenUpdate, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    """Actualiza contenido o estado de firma de un dictamen"""
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

@router.post("/{dictamen_id}/firmar", response_model=DictamenResponse)
def firmar_dictamen(
    dictamen_id: int, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    """
    Firma un dictamen.
    
    **Comportamiento:**
    - Si es APROBADO: Genera PDF firmado, lo guarda y retorna archivo_url
    - Si es OBSERVADO: Solo marca como firmado (no genera PDF)
    
    **Retorna:**
    - DictamenResponse con archivo_url poblado si es aprobado
    """
    if current_user.rol not in [RolEnum.COORDINADOR, RolEnum.ADMINISTRADOR]:
        raise HTTPException(status_code=403, detail="Solo coordinadores pueden firmar")
    
    dictamen = db.query(Dictamen).filter(Dictamen.id == dictamen_id).first()
    if not dictamen:
        raise HTTPException(status_code=404, detail="Dictamen no encontrado")
    
    if not dictamen.contenido:
        raise HTTPException(status_code=400, detail="El dictamen no tiene contenido")
    
    # Solo generar PDF si es APROBADO
    if dictamen.tipo_dictamen and dictamen.tipo_dictamen.lower() == "aprobado":
        try:
            exp = db.query(Expediente).filter(Expediente.id == dictamen.expediente_id).first()
            if not exp:
                raise HTTPException(status_code=404, detail="Expediente no encontrado")
            
            # Obtener investigadores
            investigador = db.query(User).filter(User.id == exp.investigador_id).first()
            nombres_investigadores = f"{investigador.nombre} {investigador.apellido}" if investigador else "No especificado"
            
            # Generar PDF
            fecha_firma = datetime.utcnow()
            pdf_path = generar_pdf_dictamen(
                numero_dictamen=dictamen.numero_dictamen or "DICT-SIN-NUMERO",
                tipo_dictamen=dictamen.tipo_dictamen,
                contenido=dictamen.contenido,
                titulo_protocolo=exp.titulo_protocolo,
                investigadores=nombres_investigadores,
                fecha_firma=fecha_firma
            )
            
            # Guardar ruta en BD
            dictamen.archivo_url = pdf_path
            dictamen.fecha_firma = fecha_firma
            dictamen.firmado = True
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error generando PDF: {str(e)}")
    else:
        # Para OBSERVADO, solo marcar como firmado sin generar PDF
        dictamen.fecha_firma = datetime.utcnow()
        dictamen.firmado = True
    
    db.commit()
    db.refresh(dictamen)
    return dictamen

@router.get("/{dictamen_id}/descargar")
async def descargar_dictamen(
    dictamen_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Descarga el PDF del dictamen aprobado.
    
    **Autenticación:** Requerida
    
    **Respuesta:**
    - Content-Type: application/pdf
    - Content-Disposition: attachment; filename="DICT-XXXX.pdf"
    """
    dictamen = db.query(Dictamen).filter(Dictamen.id == dictamen_id).first()
    if not dictamen:
        raise HTTPException(status_code=404, detail="Dictamen no encontrado")
    
    if not dictamen.archivo_url:
        raise HTTPException(
            status_code=400, 
            detail="Este dictamen no tiene PDF disponible (solo aprobados generan PDF)"
        )
    
    pdf_path = Path(dictamen.archivo_url)
    if not pdf_path.exists():
        raise HTTPException(status_code=404, detail="Archivo PDF no encontrado en almacenamiento")
    
    return FileResponse(
        path=pdf_path,
        media_type="application/pdf",
        filename=f"{dictamen.numero_dictamen}.pdf"
    )