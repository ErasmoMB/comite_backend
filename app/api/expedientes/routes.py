from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse, StreamingResponse
import mimetypes
from urllib.parse import quote
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
import uuid

from app.db.database import get_db
from app.models import (
    User, RolEnum, EstadoExpedienteEnum, Expediente, Documento, Bitacora,
    HistorialExpediente, Evaluacion, AutorExpediente,
    ROL_A_MODALIDAD, PROGRAMAS_ESTUDIOS, CICLOS, CICLOS_CAMBIO_TITULO, NIVELES_POSGRADO,
    DOCUMENTOS_REQUERIDOS, DOCUMENTO_LABELS, DOCUMENTO_FORMATOS, ModalidadEnum, TipoTramiteEnum,
    DOCUMENTO_INDICACIONES, DOCUMENTO_PLANTILLA, GUIA_NOMBRES, DOC_SOLICITUD_CAMBIO_TITULO,
    ESTADOS_ELEGIBLE_CAMBIO_TITULO,
)


def _doc_info(tipo):
    """Arma la info de un documento para el formulario dinámico."""
    return {
        "tipo": tipo,
        "label": DOCUMENTO_LABELS.get(tipo, tipo),
        "indicaciones": DOCUMENTO_INDICACIONES.get(tipo, []),
        "plantilla": DOCUMENTO_PLANTILLA.get(tipo),
    }
from app.schemas import (
    ExpedienteCreate, ExpedienteResponse, ExpedienteUpdate, DocumentoResponse,
    SubsanacionResponse, CambioTituloCreate,
)
from app.api.auth.routes import get_current_user

router = APIRouter()


def _autor_incompleto(autor, modalidad):
    """Devuelve la lista de datos que le faltan a un autor según la modalidad."""
    faltan = []
    if not (autor.apellidos_nombres or "").strip():
        faltan.append("apellidos y nombres")
    if not (autor.correo or "").strip():
        faltan.append("correo")
    if not (autor.telefono or "").strip():
        faltan.append("teléfono")
    if modalidad in (ModalidadEnum.PREGRADO.value, ModalidadEnum.POSTGRADO.value) and not (autor.codigo_estudiante or "").strip():
        faltan.append("código de estudiante")
    return faltan


def validar_completitud(exp):
    """Devuelve la lista de requisitos faltantes para enviar el trámite."""
    faltantes = []
    es_cambio = exp.tipo_tramite == TipoTramiteEnum.CAMBIO_TITULO.value

    if es_cambio:
        if not (exp.numero_acta or "").strip():
            faltantes.append("N° de acta")
        if not (exp.programa_estudios or "").strip():
            faltantes.append("Programa de estudios")
        if not (exp.ciclo or "").strip():
            faltantes.append("Ciclo")
        if not (exp.titulo_anterior or "").strip():
            faltantes.append("Título antiguo (original)")
        if not (exp.titulo_nuevo or "").strip():
            faltantes.append("Nuevo título")
        if not exp.autores:
            faltantes.append("Al menos un integrante")
        else:
            for a in exp.autores:
                falta = []
                if not (a.apellidos_nombres or "").strip():
                    falta.append("apellidos y nombres")
                if not (a.codigo_estudiante or "").strip():
                    falta.append("código de estudiante")
                if not (a.correo or "").strip():
                    falta.append("correo")
                if falta:
                    faltantes.append(f"Integrante '{a.apellidos_nombres or '—'}': falta {', '.join(falta)}")
        docs_requeridos = [DOC_SOLICITUD_CAMBIO_TITULO]
    else:
        if not (exp.titulo_protocolo or "").strip():
            faltantes.append("Título del proyecto")
        if not (exp.programa_estudios or "").strip():
            faltantes.append("Programa de estudios")
        if exp.modalidad == ModalidadEnum.PREGRADO.value and not (exp.ciclo or "").strip():
            faltantes.append("Ciclo")
        if exp.modalidad == ModalidadEnum.POSTGRADO.value and not (exp.nivel_posgrado or "").strip():
            faltantes.append("Nivel de posgrado")
        if not exp.autores:
            faltantes.append("Al menos un autor/integrante")
        else:
            for a in exp.autores:
                falta = _autor_incompleto(a, exp.modalidad)
                if falta:
                    faltantes.append(f"Integrante '{a.apellidos_nombres or '—'}': falta {', '.join(falta)}")
        docs_requeridos = DOCUMENTOS_REQUERIDOS.get(exp.modalidad, [])

    presentes = {d.tipo_documento for d in exp.documentos}
    for tipo in docs_requeridos:
        if tipo not in presentes:
            faltantes.append(f"Documento: {DOCUMENTO_LABELS.get(tipo, tipo)}")
    return faltantes

def generar_codigo_anual(db):
    """Código incremental global por año: 1-2026, 2-2026, ... Se asigna al ENVIAR."""
    year = datetime.utcnow().year
    sufijo = f"-{year}"
    max_n = 0
    for (cod,) in db.query(Expediente.codigo_unico).filter(Expediente.codigo_unico.like(f"%{sufijo}")).all():
        try:
            n = int(cod.split("-")[0])
            if n > max_n:
                max_n = n
        except (ValueError, AttributeError):
            continue
    return f"{max_n + 1}-{year}"

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

@router.get("/catalogos")
def get_catalogos(current_user: User = Depends(get_current_user)):
    """Catálogos y requisitos para armar el formulario dinámico de envío."""
    modalidad = ROL_A_MODALIDAD.get(current_user.rol)
    return {
        "modalidad": modalidad,  # pregrado / postgrado / interno / null
        "programas_estudios": PROGRAMAS_ESTUDIOS,
        "ciclos": CICLOS,
        "niveles_posgrado": NIVELES_POSGRADO,
        "documentos_requeridos": {
            m: [_doc_info(t) for t in docs]
            for m, docs in DOCUMENTOS_REQUERIDOS.items()
        },
        "guia_nombres": GUIA_NOMBRES,
        "cambio_titulo": {
            "ciclos": CICLOS_CAMBIO_TITULO,
            "documento": _doc_info(DOC_SOLICITUD_CAMBIO_TITULO),
        },
    }


@router.get("/{expediente_id}/requisitos")
def get_requisitos(expediente_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Checklist de completitud del expediente (para mostrar qué falta antes de enviar)."""
    exp = db.query(Expediente).filter(Expediente.id == expediente_id).first()
    if not exp:
        raise HTTPException(status_code=404, detail="Expediente no encontrado")
    if current_user.rol in ROL_A_MODALIDAD and exp.investigador_id != current_user.id:
        raise HTTPException(status_code=403, detail="No tienes acceso a este expediente")
    faltantes = validar_completitud(exp)
    requeridos = [
        {"tipo": t, "label": DOCUMENTO_LABELS.get(t, t)}
        for t in DOCUMENTOS_REQUERIDOS.get(exp.modalidad, [])
    ]
    return {"completo": len(faltantes) == 0, "faltantes": faltantes, "documentos_requeridos": requeridos}


@router.get("/elegibles-cambio-titulo")
def get_proyectos_elegibles_cambio_titulo(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Proyectos del usuario que pueden solicitar cambio de título: solo los
    ya aprobados (con o sin observaciones)."""
    proyectos = db.query(Expediente).filter(
        Expediente.investigador_id == current_user.id,
        Expediente.estado.in_(ESTADOS_ELEGIBLE_CAMBIO_TITULO),
        Expediente.tipo_tramite != TipoTramiteEnum.CAMBIO_TITULO.value,
    ).all()
    return [
        {
            "id": p.id,
            "codigo": p.codigo_unico,
            "titulo": p.titulo_protocolo,
            "estado": p.estado,
            "programa_estudios": p.programa_estudios,
            "ciclo": p.ciclo,
            "autores": [
                {
                    "apellidos_nombres": a.apellidos_nombres,
                    "codigo_estudiante": a.codigo_estudiante or "",
                    "correo": a.correo or "",
                }
                for a in sorted(p.autores, key=lambda x: x.orden or 1)
            ],
        }
        for p in proyectos
    ]


@router.get("/{expediente_id}", response_model=ExpedienteResponse)
def get_expediente(expediente_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    exp = db.query(Expediente).filter(Expediente.id == expediente_id).first()
    if not exp:
        raise HTTPException(status_code=404, detail="Expediente no encontrado")
    if current_user.rol in ROL_A_MODALIDAD and exp.investigador_id != current_user.id:
        raise HTTPException(status_code=403, detail="No tienes acceso a este expediente")
    return exp

@router.post("/", response_model=ExpedienteResponse)
def create_expediente(expediente: ExpedienteCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # La modalidad se deriva del rol con el que inició sesión (no se confía en el cliente).
    modalidad = ROL_A_MODALIDAD.get(current_user.rol)
    if not modalidad:
        raise HTTPException(status_code=403, detail="Tu rol no puede enviar proyectos al comité.")

    # Validación de catálogos controlados (si vienen).
    if expediente.programa_estudios and expediente.programa_estudios not in PROGRAMAS_ESTUDIOS:
        raise HTTPException(status_code=400, detail="Programa de estudios no válido.")
    if expediente.ciclo and expediente.ciclo not in CICLOS:
        raise HTTPException(status_code=400, detail="Ciclo no válido.")
    if expediente.nivel_posgrado and expediente.nivel_posgrado not in NIVELES_POSGRADO:
        raise HTTPException(status_code=400, detail="Nivel de posgrado no válido.")

    new_exp = Expediente(
        titulo_protocolo=expediente.titulo_protocolo,
        tipo_tramite=expediente.tipo_tramite or "proyecto_nuevo",
        facultad=expediente.facultad,
        modalidad=modalidad,
        programa_estudios=expediente.programa_estudios,
        # Cada campo solo aplica a su modalidad.
        ciclo=expediente.ciclo if modalidad == ModalidadEnum.PREGRADO.value else None,
        nivel_posgrado=expediente.nivel_posgrado if modalidad == ModalidadEnum.POSTGRADO.value else None,
        investigador_id=current_user.id,
        estado=EstadoExpedienteEnum.BORRADOR,
        codigo_unico=None,  # el código formal N-AÑO se asigna recién al enviar
    )
    db.add(new_exp)
    db.flush()  # obtener new_exp.id para los autores

    for i, autor in enumerate(expediente.autores, start=1):
        db.add(AutorExpediente(
            expediente_id=new_exp.id,
            orden=i,
            apellidos_nombres=autor.apellidos_nombres,
            codigo_estudiante=autor.codigo_estudiante if modalidad != ModalidadEnum.INTERNO.value else None,
            correo=autor.correo,
            telefono=autor.telefono,
            es_principal=(i == 1),
        ))

    registrar_bitacora(db, new_exp.id, "Expediente creado", f"Título: {expediente.titulo_protocolo}", current_user.id)
    db.commit()
    db.refresh(new_exp)
    return new_exp

@router.post("/cambio-titulo", response_model=ExpedienteResponse)
def create_cambio_titulo(payload: CambioTituloCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Crea una solicitud de cambio de título (trámite distinto a un proyecto nuevo)."""
    modalidad = ROL_A_MODALIDAD.get(current_user.rol)
    if not modalidad:
        raise HTTPException(status_code=403, detail="Tu rol no puede solicitar un cambio de título.")
    if payload.programa_estudios not in PROGRAMAS_ESTUDIOS:
        raise HTTPException(status_code=400, detail="Programa de estudios no válido.")
    if payload.ciclo not in CICLOS_CAMBIO_TITULO:
        raise HTTPException(status_code=400, detail="Ciclo no válido.")

    # El proyecto origen debe ser del usuario y estar aprobado (con o sin observaciones).
    origen = db.query(Expediente).filter(Expediente.id == payload.proyecto_origen_id).first()
    if not origen or origen.investigador_id != current_user.id:
        raise HTTPException(status_code=404, detail="Proyecto de origen no encontrado.")
    if origen.estado not in ESTADOS_ELEGIBLE_CAMBIO_TITULO:
        raise HTTPException(status_code=400, detail="Solo puedes solicitar cambio de título de un proyecto aprobado.")

    # El N° de acta se deriva del código del proyecto origen (ej. "1-2026" -> "1").
    numero_acta = (origen.codigo_unico or "").split("-")[0] or None

    new_exp = Expediente(
        # El título del proyecto pasa a ser el nuevo título (para listados).
        titulo_protocolo=payload.titulo_nuevo,
        tipo_tramite=TipoTramiteEnum.CAMBIO_TITULO.value,
        modalidad=modalidad,
        programa_estudios=payload.programa_estudios,
        ciclo=payload.ciclo,
        numero_acta=numero_acta,
        titulo_anterior=origen.titulo_protocolo,  # autollenado desde el proyecto origen
        titulo_nuevo=payload.titulo_nuevo,
        proyecto_origen_id=origen.id,
        investigador_id=current_user.id,
        estado=EstadoExpedienteEnum.BORRADOR,
        codigo_unico=None,
    )
    db.add(new_exp)
    db.flush()

    for i, autor in enumerate(payload.autores, start=1):
        db.add(AutorExpediente(
            expediente_id=new_exp.id,
            orden=i,
            apellidos_nombres=autor.apellidos_nombres,
            codigo_estudiante=autor.codigo_estudiante,
            correo=autor.correo,
            telefono=None,  # el cambio de título no pide teléfono
            es_principal=(i == 1),
        ))

    registrar_bitacora(db, new_exp.id, "Solicitud de cambio de título creada",
                       f"Nuevo título: {payload.titulo_nuevo}", current_user.id)
    db.commit()
    db.refresh(new_exp)
    return new_exp


@router.put("/{expediente_id}", response_model=ExpedienteResponse)
def update_expediente(expediente_id: int, exp_update: ExpedienteUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    exp = db.query(Expediente).filter(Expediente.id == expediente_id).first()
    if not exp:
        raise HTTPException(status_code=404, detail="Expediente no encontrado")
    if exp.estado != EstadoExpedienteEnum.BORRADOR and current_user.rol in ROL_A_MODALIDAD:
        raise HTTPException(status_code=403, detail="No puedes modificar un expediente enviado")
    if exp_update.titulo_protocolo:
        exp.titulo_protocolo = exp_update.titulo_protocolo
    if exp_update.tipo_tramite is not None:
        exp.tipo_tramite = exp_update.tipo_tramite
    if exp_update.facultad is not None:
        exp.facultad = exp_update.facultad
    if exp_update.estado:
        actualizar_estado(db, exp, exp_update.estado)
        registrar_bitacora(db, exp.id, f"Estado cambiado a {exp_update.estado}", None, current_user.id)
    db.commit()
    db.refresh(exp)
    return exp

@router.delete("/{expediente_id}")
def delete_expediente(expediente_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """El autor puede eliminar su proyecto solo mientras esté en BORRADOR."""
    exp = db.query(Expediente).filter(Expediente.id == expediente_id).first()
    if not exp:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    if exp.investigador_id != current_user.id:
        raise HTTPException(status_code=403, detail="Solo el autor puede eliminar su proyecto.")
    if exp.estado != EstadoExpedienteEnum.BORRADOR:
        raise HTTPException(status_code=400, detail="Solo puedes eliminar proyectos en estado borrador.")

    # Borrar dependencias (no hay evaluaciones/dictámenes en borrador).
    db.query(Documento).filter(Documento.expediente_id == expediente_id).delete()
    db.query(AutorExpediente).filter(AutorExpediente.expediente_id == expediente_id).delete()
    db.query(Bitacora).filter(Bitacora.expediente_id == expediente_id).delete()
    db.query(HistorialExpediente).filter(HistorialExpediente.expediente_id == expediente_id).delete()
    db.delete(exp)
    db.commit()
    return {"message": "Proyecto eliminado"}


@router.post("/{expediente_id}/enviar")
def enviar_expediente(expediente_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    exp = db.query(Expediente).filter(Expediente.id == expediente_id).first()
    if not exp:
        raise HTTPException(status_code=404, detail="Expediente no encontrado")
    if exp.investigador_id != current_user.id:
        raise HTTPException(status_code=403, detail="No tienes acceso")
    if exp.estado != EstadoExpedienteEnum.BORRADOR:
        raise HTTPException(status_code=400, detail="El expediente ya fue enviado")
    # La fecha límite aplica solo a proyectos nuevos (no al cambio de título).
    from app.api.config.routes import leer_config, CLAVE_FECHA_LIMITE
    fecha_str = leer_config(db, CLAVE_FECHA_LIMITE)
    if fecha_str and exp.tipo_tramite != TipoTramiteEnum.CAMBIO_TITULO.value:
        try:
            limite = datetime.fromisoformat(fecha_str.replace("Z", "+00:00"))
            ahora = datetime.now(limite.tzinfo) if limite.tzinfo else datetime.utcnow()
            if ahora > limite:
                raise HTTPException(
                    status_code=403,
                    detail="Los envíos están cerrados: la fecha límite ya venció.",
                )
        except ValueError:
            pass
    # No se permite enviar un expediente incompleto.
    faltantes = validar_completitud(exp)
    if faltantes:
        raise HTTPException(
            status_code=400,
            detail={"mensaje": "El expediente está incompleto. Completa lo siguiente antes de enviar.", "faltantes": faltantes},
        )
    # Asignar el código formal incremental del año recién al enviar.
    if not exp.codigo_unico:
        exp.codigo_unico = generar_codigo_anual(db)
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
    # Validaciones. Cada tipo de documento exige su formato exacto; si el tipo
    # no está en el catálogo, se aplica el set amplio (compatibilidad).
    formato = DOCUMENTO_FORMATOS.get(tipo_documento)
    if formato:
        TIPOS_PERMITIDOS = formato["mimes"]
        EXTENSIONES_PERMITIDAS = formato["ext"]
        FORMATO_DESC = formato["desc"]
    else:
        TIPOS_PERMITIDOS = {"application/pdf", "application/msword",
                            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                            "application/vnd.ms-excel",
                            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            "text/plain"}
        EXTENSIONES_PERMITIDAS = {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".txt"}
        FORMATO_DESC = "PDF, DOC, DOCX, XLS, XLSX, TXT"
    TAMAÑO_MAXIMO = 10 * 1024 * 1024  # 10 MB

    # Validar extensión (criterio principal; el MIME del navegador no siempre es fiable)
    from pathlib import Path as PathlibPath
    file_ext = PathlibPath(file.filename).suffix.lower()
    if file_ext not in EXTENSIONES_PERMITIDAS:
        raise HTTPException(
            status_code=400,
            detail=f"Este documento solo admite: {FORMATO_DESC}. Subiste un archivo {file_ext or 'sin extensión'}.",
        )

    # Validar MIME type (si el navegador lo envía)
    if file.content_type and file.content_type not in TIPOS_PERMITIDOS:
        raise HTTPException(
            status_code=400,
            detail=f"Este documento solo admite: {FORMATO_DESC}.",
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
    
    if current_user.rol in ROL_A_MODALIDAD and exp.investigador_id != current_user.id:
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
    if current_user.rol in ROL_A_MODALIDAD and exp.investigador_id != current_user.id:
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
        # S3 storage: stream file from S3 through backend
        try:
            import boto3
            import os
            import httpx
            
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
            
            # Fetch from S3 and stream to client
            response = httpx.get(presigned_url)
            response.raise_for_status()
            
            return StreamingResponse(
                iter([response.content]),
                media_type=content_type,
                headers=headers
            )
        except Exception as e:
            print(f"Error accediendo a S3: {e}")
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
    if current_user.rol in ROL_A_MODALIDAD and exp.investigador_id != current_user.id:
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
        # S3 storage: stream file from S3 through backend
        try:
            import boto3
            import os
            import httpx
            
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
            
            # Fetch from S3 and stream to client
            response = httpx.get(presigned_url)
            response.raise_for_status()
            
            return StreamingResponse(
                iter([response.content]),
                media_type=content_type,
                headers=headers
            )
        except Exception as e:
            print(f"Error accediendo a S3: {e}")
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