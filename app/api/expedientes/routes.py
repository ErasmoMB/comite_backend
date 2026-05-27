from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
import mimetypes
from urllib.parse import quote
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

@router.post(
    "/{expediente_id}/documentos", 
    response_model=DocumentoResponse,
    summary="Subir documento a expediente",
    description="""
    Sube un documento a un expediente.

    **Validaciones:**
    - Tipos MIME permitidos: application/pdf, application/msword, application/vnd.openxmlformats-officedocument.wordprocessingml.document, application/vnd.ms-excel, application/vnd.openxmlformats-officedocument.spreadsheetml.sheet, text/plain
    - Extensiones permitidas: .pdf, .doc, .docx, .xls, .xlsx, .txt
    - Tamaño máximo: 10 MB
    """,
    responses={
        400: {"description": "Archivo no válido (tipo, extensión o tamaño incorrecto)"},
        404: {"description": "Expediente no encontrado"},
    }
)
async def upload_documento(
    expediente_id: int, 
    file: UploadFile = File(..., description="Archivo a subir (PDF, DOC, DOCX, XLS, XLSX, TXT - máx 10MB)"), 
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
    import boto3
    from datetime import datetime
    
    # Generar nombre único para evitar conflictos
    nombre_base = PathlibPath(file.filename).stem
    extension = PathlibPath(file.filename).suffix
    nombre_unico = f"{nombre_base}_{uuid.uuid4().hex[:8]}{extension}"
    
    # Try S3 upload first
    ruta_final = None
    try:
        s3_client = boto3.client(
            's3',
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
            region_name=os.getenv('AWS_S3_REGION', 'us-east-1')
        )
        
        # Upload to S3
        s3_key = f"uploads/{expediente_id}/{nombre_unico}"
        s3_client.put_object(
            Bucket=os.getenv('AWS_S3_BUCKET', 'comite-etica-pdfs'),
            Key=s3_key,
            Body=contenido,
            ContentType=file.content_type
        )
        
        ruta_final = s3_key
        print(f"Documento subido a S3: {s3_key}")
    except Exception as e:
        print(f"Error subiendo a S3: {e}. Usando almacenamiento local...")
        
        # Fallback to local storage
        upload_dir = Path("uploads") / str(expediente_id)
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = upload_dir / nombre_unico
        with open(file_path, "wb") as buffer:
            buffer.write(contenido)
        
        ruta_final = str(file_path)
    
    doc = Documento(
        expediente_id=expediente_id, 
        nombre_archivo=file.filename, 
        tipo_documento=tipo_documento, 
        es_obligatorio=es_obligatorio,
        ruta_archivo=ruta_final
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    registrar_bitacora(db, expediente_id, "Documento subido", 
                      f"Archivo: {file.filename} (MIME: {file.content_type}, Tamaño: {len(contenido)} bytes)", 
                      current_user.id)
    db.commit()
    return doc


@router.get("/{expediente_id}/documentos", response_model=List[DocumentoResponse])
def get_documentos(
    expediente_id: int, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    """
    Lista todos los documentos asociados a un expediente.
    """
    exp = db.query(Expediente).filter(Expediente.id == expediente_id).first()
    if not exp:
        raise HTTPException(status_code=404, detail="Expediente no encontrado")
    
    if current_user.rol == RolEnum.INVESTIGADOR and exp.investigador_id != current_user.id:
        raise HTTPException(status_code=403, detail="No tienes acceso a este expediente")
    
    documentos = db.query(Documento).filter(Documento.expediente_id == expediente_id).all()
    return documentos

@router.get(
    "/{expediente_id}/documentos/{documento_id}/descargar",
    summary="Descargar documento",
    description="Descarga un documento específico de un expediente.",
    responses={
        200: {
            "content": {"application/octet-stream": {}},
            "description": "Archivo descargado exitosamente",
            "headers": {
                "Content-Disposition": {"description": "Nombre del archivo para descargar", "schema": {"type": "string"}},
                "Content-Type": {"description": "Tipo MIME del archivo", "schema": {"type": "string"}},
                "Content-Length": {"description": "Tamaño del archivo", "schema": {"type": "integer"}},
            }
        },
        403: {"description": "No tienes acceso a este expediente"},
        404: {"description": "Expediente o documento no encontrado"},
        400: {"description": "Documento sin ruta de archivo"},
    }
)
async def descargar_documento(
    expediente_id: int,
    documento_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Descarga un documento específico de un expediente.
    
    **Acceso:**
    - Investigador: Solo sus propios expedientes
    - Admin/Coordinador/Secretaria: Todos los expedientes
    - Evaluador: Expedientes que le fueron asignados
    
    **Response Headers:**
    - Content-Type: Detectado automáticamente (PDF, DOCX, XLSX, TXT, etc.)
    - Content-Disposition: attachment; filename con UTF-8 encoding
    - Access-Control-Expose-Headers: Para acceso desde frontend
    """
    # Validar que el expediente existe
    exp = db.query(Expediente).filter(Expediente.id == expediente_id).first()
    if not exp:
        raise HTTPException(status_code=404, detail="Expediente no encontrado")
    
    # Validar acceso al expediente
    if current_user.rol == RolEnum.INVESTIGADOR and exp.investigador_id != current_user.id:
        raise HTTPException(status_code=403, detail="No tienes acceso a este expediente")
    
    if current_user.rol == RolEnum.EVALUADOR:
        # Verificar que sea evaluador asignado
        evaluacion = db.query(Evaluacion).filter(
            Evaluacion.expediente_id == expediente_id,
            Evaluacion.evaluador_id == current_user.id
        ).first()
        if not evaluacion:
            raise HTTPException(status_code=403, detail="No tienes acceso a este expediente")
    
    # Buscar el documento
    doc = db.query(Documento).filter(
        Documento.id == documento_id,
        Documento.expediente_id == expediente_id
    ).first()
    
    if not doc:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    
    if not doc.ruta_archivo:
        raise HTTPException(status_code=400, detail="Documento sin ruta de archivo")
    
    # Registrar descarga en bitácora
    registrar_bitacora(
        db,
        expediente_id,
        "Documento descargado",
        f"Documento: {doc.nombre_archivo} (ID: {documento_id})",
        current_user.id
    )
    db.commit()
    
    # Detectar Content-Type
    content_type, _ = mimetypes.guess_type(str(doc.ruta_archivo))
    if not content_type:
        content_type = "application/octet-stream"
    
    # Headers para descarga (attachment)
    filename_utf8 = quote(doc.nombre_archivo, safe='')
    headers = {
        "Content-Disposition": f'attachment; filename="{doc.nombre_archivo}"; filename*=UTF-8\'\'{filename_utf8}',
        "Access-Control-Expose-Headers": "Content-Disposition, Content-Type, Content-Length",
    }
    
    # Check if file is in S3
    if doc.ruta_archivo.startswith('uploads/'):
        # S3 storage: generate presigned URL and redirect
        try:
            import boto3
            import os
            
            s3_client = boto3.client(
                's3',
                aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
                aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
                region_name=os.getenv('AWS_S3_REGION', 'us-east-1')
            )
            
            presigned_url = s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': os.getenv('AWS_S3_BUCKET', 'comite-etica-pdfs'), 'Key': doc.ruta_archivo},
                ExpiresIn=3600
            )
            
            from fastapi.responses import RedirectResponse
            return RedirectResponse(url=presigned_url, headers=headers)
        except Exception as e:
            print(f"Error generando presigned URL: {e}")
            raise HTTPException(status_code=500, detail="Error al acceder al documento")
    else:
        # Local storage
        from pathlib import Path
        file_path = Path(doc.ruta_archivo)
        
        # Validar que el archivo existe
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Archivo no encontrado en servidor")
        
        return FileResponse(
            path=file_path,
            media_type=content_type,
            headers=headers
        )

@router.get(
    "/{expediente_id}/documentos/{documento_id}/preview",
    summary="Previsualizar documento",
    description="Previsualiza un documento en el navegador (abre inline).",
    responses={
        200: {
            "content": {"application/octet-stream": {}},
            "description": "Documento para previsualizar en navegador",
            "headers": {
                "Content-Disposition": {"description": "inline; filename", "schema": {"type": "string"}},
                "Content-Type": {"description": "Tipo MIME del archivo", "schema": {"type": "string"}},
            }
        },
        403: {"description": "No tienes acceso a este expediente"},
        404: {"description": "Expediente o documento no encontrado"},
    }
)
async def preview_documento(
    expediente_id: int,
    documento_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Previsualiza un documento en el navegador (abre en pestaña nueva).
    
    **Diferencia con /descargar:**
    - `/descargar` → Content-Disposition: attachment (descarga archivo)
    - `/preview` → Content-Disposition: inline (abre en navegador para PDFs)
    
    **Acceso:**
    - Investigador: Solo sus propios expedientes
    - Admin/Coordinador/Secretaria: Todos los expedientes
    - Evaluador: Expedientes que le fueron asignados
    """
    from pathlib import Path
    
    # Validar que el expediente existe
    exp = db.query(Expediente).filter(Expediente.id == expediente_id).first()
    if not exp:
        raise HTTPException(status_code=404, detail="Expediente no encontrado")
    
    # Validar acceso al expediente
    if current_user.rol == RolEnum.INVESTIGADOR and exp.investigador_id != current_user.id:
        raise HTTPException(status_code=403, detail="No tienes acceso a este expediente")
    
    if current_user.rol == RolEnum.EVALUADOR:
        evaluacion = db.query(Evaluacion).filter(
            Evaluacion.expediente_id == expediente_id,
            Evaluacion.evaluador_id == current_user.id
        ).first()
        if not evaluacion:
            raise HTTPException(status_code=403, detail="No tienes acceso a este expediente")
    
    # Buscar el documento
    doc = db.query(Documento).filter(
        Documento.id == documento_id,
        Documento.expediente_id == expediente_id
    ).first()
    
    if not doc:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    
    if not doc.ruta_archivo:
        raise HTTPException(status_code=400, detail="Documento sin ruta de archivo")
    
    # Registrar preview en bitácora
    registrar_bitacora(
        db,
        expediente_id,
        "Documento previsualizador",
        f"Archivo: {doc.nombre_archivo} (ID: {documento_id})",
        current_user.id
    )
    db.commit()
    
    # Detectar Content-Type
    content_type, _ = mimetypes.guess_type(str(doc.ruta_archivo))
    if not content_type:
        content_type = "application/octet-stream"
    
    # Headers para preview (inline)
    filename_utf8 = quote(doc.nombre_archivo, safe='')
    headers = {
        "Content-Disposition": f'inline; filename="{doc.nombre_archivo}"; filename*=UTF-8\'\'{filename_utf8}',
        "Access-Control-Expose-Headers": "Content-Disposition, Content-Type, Content-Length",
    }
    
    # Check if file is in S3
    if doc.ruta_archivo.startswith('uploads/'):
        # S3 storage: generate presigned URL and redirect
        try:
            import boto3
            import os
            
            s3_client = boto3.client(
                's3',
                aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
                aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
                region_name=os.getenv('AWS_S3_REGION', 'us-east-1')
            )
            
            presigned_url = s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': os.getenv('AWS_S3_BUCKET', 'comite-etica-pdfs'), 'Key': doc.ruta_archivo},
                ExpiresIn=3600
            )
            
            from fastapi.responses import RedirectResponse
            return RedirectResponse(url=presigned_url, headers=headers)
        except Exception as e:
            print(f"Error generando presigned URL: {e}")
            raise HTTPException(status_code=500, detail="Error al acceder al documento")
    else:
        # Local storage
        file_path = Path(doc.ruta_archivo)
        
        # Validar que el archivo existe
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Archivo no encontrado en servidor")
        
        return FileResponse(
            path=file_path,
            media_type=content_type,
            headers=headers
        )
@router.post(
    "/{expediente_id}/subsanacion", 
    response_model=SubsanacionResponse,
    summary="Registrar subsanación",
    description="""
    Registra la respuesta de subsanación del investigador a las observaciones.
    
    El investigador debe estar en estado SUBSANACION para poder enviar la subsanación.
    Esta ответа permite al investigador responder a las observaciones de los evaluadores.
    """,
    responses={
        400: {"description": "El expediente no está en estado SUBSANACION"},
        404: {"description": "Expediente no encontrado"},
    }
)
async def submit_subsanacion(
    expediente_id: int,
    observaciones: str = Form(..., description="Respuesta del investigador a las observaciones"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
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