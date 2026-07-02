from fastapi import APIRouter, Depends, HTTPException, Body
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session, joinedload
from typing import List
from datetime import datetime
from pathlib import Path

from app.db.database import get_db
from app.models import User, RolEnum, Expediente, Evaluacion, EvaluacionCriterio, AutorExpediente, EstadoExpedienteEnum, Notificacion, CRITERIOS_RUBRICA, PUNTAJE_TOTAL_MAX, CRITERIOS_MAX_POR_KEY, resultado_por_puntaje
from app.schemas import EvaluacionCreate, EvaluacionResponse, EvaluacionUpdate, EvaluacionAsignarRequest, RubricaResponse, CriterioRubricaItem
from app.api.auth.routes import get_current_user
from app.utils.pdf_generator import guardar_pdf_evaluacion
from app.utils.email_service import enviar_email

router = APIRouter()


def _generar_dictamen_para_evaluacion(db: Session, evaluacion: Evaluacion) -> str | None:
    """Genera el PDF de dictamen para una evaluación aprobada."""
    from datetime import datetime
    from app.utils.pdf_generator import generar_pdf_dictamen

    expediente = db.query(Expediente).options(
        joinedload(Expediente.investigador)
    ).filter(Expediente.id == evaluacion.expediente_id).first()
    if not expediente:
        return None

    resultado_label = {
        "aprobado": "Aprobado",
        "aprobado_observaciones": "Aprobado con observaciones",
    }.get(evaluacion.resultado, "Aprobado")

    numero = f"DIC-{(expediente.codigo_unico or str(expediente.id)).replace('/', '-')}"
    fecha = datetime.now().strftime("%d/%m/%Y")
    inv_nombre = expediente.investigador_nombre or ""

    contenido = (
        f"El Comité de Ética en Investigación, después de evaluar el proyecto "
        f"titulado \"{expediente.titulo_protocolo}\", ha determinado que el mismo "
        f"se encuentra {resultado_label.lower()}.\n\n"
        f"Puntaje obtenido: {evaluacion.puntaje_total}/20.\n\n"
        f"Observaciones: {evaluacion.observaciones or 'Ninguna.'}"
    )

    pdf_url = generar_pdf_dictamen(numero, expediente.titulo_protocolo or "", contenido, inv_nombre, fecha)
    if pdf_url and not pdf_url.startswith("http"):
        return pdf_url
    return pdf_url


def _generar_pdf_para_evaluacion(db: Session, evaluacion: Evaluacion) -> str | None:
    """Genera el PDF de evaluación y devuelve la ruta del archivo."""
    from app.models import CRITERIOS_RUBRICA as _CR

    expediente = db.query(Expediente).options(
        joinedload(Expediente.investigador)
    ).filter(Expediente.id == evaluacion.expediente_id).first()

    evaluador = db.query(User).filter(User.id == evaluacion.evaluador_id).first()

    autores = db.query(AutorExpediente).filter(
        AutorExpediente.expediente_id == evaluacion.expediente_id
    ).order_by(AutorExpediente.orden).all()

    # rebuild criterios with full metadata
    criterios_con_puntajes = []
    for idx, c in enumerate(_CR):
        match = [ec for ec in evaluacion.criterios if ec.criterio_key == c["key"]]
        puntaje = match[0].puntaje if match else 0
        obs = match[0].observacion if match else ""
        criterios_con_puntajes.append({
            **c,
            "puntaje": puntaje,
            "observacion": obs,
            "orden": idx,
        })

    return guardar_pdf_evaluacion(
        evaluacion, expediente, evaluador,
        autores, criterios_con_puntajes,
    )


@router.get("/rubrica", response_model=RubricaResponse)
def get_rubrica(current_user: User = Depends(get_current_user)):
    return RubricaResponse(
        criterios=[CriterioRubricaItem(**c) for c in CRITERIOS_RUBRICA],
        puntaje_total_max=PUNTAJE_TOTAL_MAX,
        umbrales={"aprobado": "17-20", "aprobado_observaciones": "13-16", "no_aprobado": "0-12"},
    )

@router.get("/", response_model=List[EvaluacionResponse])
def get_evaluaciones(skip: int = 0, limit: int = 50, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.rol == RolEnum.EVALUADOR:
        return db.query(Evaluacion).options(joinedload(Evaluacion.expediente).joinedload(Expediente.investigador)).filter(Evaluacion.evaluador_id == current_user.id).offset(skip).limit(limit).all()
    return db.query(Evaluacion).options(joinedload(Evaluacion.expediente).joinedload(Expediente.investigador)).offset(skip).limit(limit).all()

@router.get("/mis-evaluaciones", response_model=List[EvaluacionResponse])
def get_my_evaluaciones(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.rol != RolEnum.EVALUADOR:
        raise HTTPException(status_code=403, detail="Solo evaluadores")
    return db.query(Evaluacion).options(joinedload(Evaluacion.expediente).joinedload(Expediente.investigador)).filter(Evaluacion.evaluador_id == current_user.id).all()

@router.get("/{evaluacion_id}", response_model=EvaluacionResponse)
def get_evaluacion(evaluacion_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    evaluacion = db.query(Evaluacion).options(joinedload(Evaluacion.expediente).joinedload(Expediente.investigador)).filter(Evaluacion.id == evaluacion_id).first()
    if not evaluacion:
        raise HTTPException(status_code=404, detail="Evaluación no encontrada")
    return evaluacion

@router.post("/", response_model=EvaluacionResponse)
def create_evaluacion(evaluacion: EvaluacionCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.rol not in [RolEnum.ADMINISTRADOR, RolEnum.COORDINADOR]:
        raise HTTPException(status_code=403, detail="Solo coordinadores pueden crear evaluaciones")
    exp = db.query(Expediente).filter(Expediente.id == evaluacion.expediente_id).first()
    if not exp:
        raise HTTPException(status_code=404, detail="Expediente no encontrado")
    existentes = db.query(Evaluacion).filter(Evaluacion.expediente_id == evaluacion.expediente_id).all()
    if len(existentes) >= 1:
        raise HTTPException(status_code=400, detail="Este expediente ya tiene un evaluador asignado")
    nueva_eval = Evaluacion(expediente_id=evaluacion.expediente_id, evaluador_id=current_user.id)
    db.add(nueva_eval)
    db.commit()
    db.refresh(nueva_eval)
    # Hacer eager load del expediente antes de retornar
    db.refresh(nueva_eval, attribute_names=['expediente'])
    return nueva_eval

@router.put("/{evaluacion_id}", response_model=EvaluacionResponse)
def update_evaluacion(evaluacion_id: int, eval_update: EvaluacionUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    evaluacion = db.query(Evaluacion).options(
        joinedload(Evaluacion.expediente).joinedload(Expediente.investigador),
        joinedload(Evaluacion.criterios),
    ).filter(Evaluacion.id == evaluacion_id).first()
    if not evaluacion:
        raise HTTPException(status_code=404, detail="Evaluación no encontrada")
    if evaluacion.evaluador_id != current_user.id and current_user.rol != RolEnum.ADMINISTRADOR:
        raise HTTPException(status_code=403, detail="No puedes modificar esta evaluación")

    if eval_update.recommendation is not None:
        evaluacion.recommendation = eval_update.recommendation
    if eval_update.observaciones is not None:
        evaluacion.observaciones = eval_update.observaciones

    # Upsert de criterios (reemplaza los existentes por los enviados)
    if eval_update.criterios is not None:
        for c in eval_update.criterios:
            if c.key not in CRITERIOS_MAX_POR_KEY:
                raise HTTPException(status_code=400, detail=f"Criterio desconocido: {c.key}")
            maximo = CRITERIOS_MAX_POR_KEY[c.key]
            if c.puntaje < 0 or c.puntaje > maximo:
                raise HTTPException(status_code=400, detail=f"Puntaje de '{c.key}' debe estar entre 0 y {maximo}")
        evaluacion.criterios.clear()
        for c in eval_update.criterios:
            evaluacion.criterios.append(EvaluacionCriterio(criterio_key=c.key, puntaje=c.puntaje, observacion=c.observacion))

    if eval_update.completa is not None:
        evaluacion.completa = eval_update.completa
        if eval_update.completa:
            keys_presentes = {c.criterio_key for c in evaluacion.criterios}
            if keys_presentes != set(CRITERIOS_MAX_POR_KEY.keys()):
                raise HTTPException(status_code=400, detail="Faltan criterios por evaluar (se requieren los 7)")
            total = sum(c.puntaje for c in evaluacion.criterios)
            evaluacion.puntaje_total = total
            evaluacion.resultado = resultado_por_puntaje(total)
            evaluacion.fecha_envio = datetime.utcnow()
            if evaluacion.expediente:
                evaluacion.expediente.estado = evaluacion.resultado

    db.commit()
    db.refresh(evaluacion)
    db.refresh(evaluacion, attribute_names=['expediente', 'criterios'])

    # --- Post-submission: Generate PDFs and send emails ---
    ya_fue_enviada = evaluacion.completa and bool(evaluacion.resultado)
    if ya_fue_enviada:
        try:
            # Generar PDFs según resultado:
            #   aprobado              → dictamen solamente
            #   aprobado_observaciones → informe (rúbrica) + dictamen
            #   no_aprobado           → informe (rúbrica) solamente
            if evaluacion.resultado in ("aprobado_observaciones", "no_aprobado"):
                pdf_path = _generar_pdf_para_evaluacion(db, evaluacion)
                if pdf_path:
                    evaluacion.rubrica_pdf_path = pdf_path

            if evaluacion.resultado in ("aprobado", "aprobado_observaciones"):
                dictamen_path = _generar_dictamen_para_evaluacion(db, evaluacion)
                if dictamen_path:
                    evaluacion.dictamen_pdf_path = dictamen_path

            db.commit()

            # Email a autores
            expediente = evaluacion.expediente
            autores = db.query(AutorExpediente).filter(
                AutorExpediente.expediente_id == expediente.id
            ).order_by(AutorExpediente.orden).all()

            autor_emails = [a.correo for a in autores if a.correo]
            if not autor_emails and expediente.investigador:
                autor_emails = [expediente.investigador.email]

            if autor_emails:
                resultado_label = {
                    "aprobado": "Aprobado",
                    "aprobado_observaciones": "Aprobado con observaciones",
                    "no_aprobado": "No aprobado",
                }.get(evaluacion.resultado, evaluacion.resultado)

                subject = f"Resultado de evaluación - {expediente.codigo_unico or ''}"
                if evaluacion.resultado == "no_aprobado":
                    body = (
                        f"Estimado(a) investigador(a),\n\n"
                        f"Se ha completado la evaluación ética de su proyecto:\n"
                        f"  Título: {expediente.titulo_protocolo}\n"
                        f"  Código: {expediente.codigo_unico or ''}\n"
                        f"  Resultado: {resultado_label}\n"
                        f"  Puntaje: {evaluacion.puntaje_total}/20\n\n"
                        f"Adjunto encontrará la rúbrica de evaluación.\n\n"
                        f"Saludos cordiales,\nComité de Ética en Investigación"
                    )
                elif evaluacion.resultado == "aprobado":
                    body = (
                        f"Estimado(a) investigador(a),\n\n"
                        f"Se ha completado la evaluación ética de su proyecto:\n"
                        f"  Título: {expediente.titulo_protocolo}\n"
                        f"  Código: {expediente.codigo_unico or ''}\n"
                        f"  Resultado: {resultado_label}\n"
                        f"  Puntaje: {evaluacion.puntaje_total}/20\n\n"
                        f"Adjunto encontrará el dictamen de aprobación.\n\n"
                        f"Saludos cordiales,\nComité de Ética en Investigación"
                    )
                else:
                    body = (
                        f"Estimado(a) investigador(a),\n\n"
                        f"Se ha completado la evaluación ética de su proyecto:\n"
                        f"  Título: {expediente.titulo_protocolo}\n"
                        f"  Código: {expediente.codigo_unico or ''}\n"
                        f"  Resultado: {resultado_label}\n"
                        f"  Puntaje: {evaluacion.puntaje_total}/20\n\n"
                        f"Adjunto encontrará la rúbrica de evaluación y el dictamen correspondiente.\n\n"
                        f"Saludos cordiales,\nComité de Ética en Investigación"
                    )

                pdf_paths = []
                if evaluacion.rubrica_pdf_path:
                    pdf_paths.append(evaluacion.rubrica_pdf_path)
                if evaluacion.dictamen_pdf_path:
                    pdf_paths.append(evaluacion.dictamen_pdf_path)
                enviar_email(autor_emails, subject, body, pdf_paths)

        except Exception as e:
            import traceback
            error_msg = f"Error en post-evaluacion: {e}\n{traceback.format_exc()}"
            print(error_msg, flush=True)

    return evaluacion

@router.get("/{evaluacion_id}/descargar-rubrica")
def descargar_rubrica(
    evaluacion_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Descargar el PDF de rúbrica de una evaluación."""
    evaluacion = db.query(Evaluacion).filter(Evaluacion.id == evaluacion_id).first()
    if not evaluacion:
        raise HTTPException(status_code=404, detail="Evaluación no encontrada")

    if not evaluacion.rubrica_pdf_path:
        raise HTTPException(status_code=404, detail="La rúbrica PDF aún no ha sido generada. Debes enviar la evaluación primero.")

    pdf_path = Path(evaluacion.rubrica_pdf_path)
    if not pdf_path.exists():
        raise HTTPException(status_code=404, detail="El archivo PDF de rúbrica no se encuentra en el servidor.")

    return FileResponse(
        path=str(pdf_path),
        media_type="application/pdf",
        filename=pdf_path.name,
    )


@router.get("/{evaluacion_id}/descargar-dictamen")
def descargar_dictamen(
    evaluacion_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Descargar el PDF de dictamen de una evaluación."""
    evaluacion = db.query(Evaluacion).filter(Evaluacion.id == evaluacion_id).first()
    if not evaluacion:
        raise HTTPException(status_code=404, detail="Evaluación no encontrada")

    if not evaluacion.dictamen_pdf_path:
        raise HTTPException(status_code=404, detail="El dictamen PDF aún no ha sido generado. Solo se genera para evaluaciones aprobadas.")

    pdf_path = Path(evaluacion.dictamen_pdf_path)
    if not pdf_path.exists():
        raise HTTPException(status_code=404, detail="El archivo PDF de dictamen no se encuentra en el servidor.")

    return FileResponse(
        path=str(pdf_path),
        media_type="application/pdf",
        filename=pdf_path.name,
    )


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
    db.commit()
    return {"message": "Guardado parcial exitoso"}


@router.post("/expediente/{expediente_id}/asignar")
def asignar_evaluador_manual(
    expediente_id: int, 
    request: EvaluacionAsignarRequest,
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    """
    Permite al coordinador asignar manualmente un evaluador a un expediente.
    Solo coordinadores y administradores pueden usar este endpoint.
    """
    evaluador_id = request.evaluador_id
    
    if current_user.rol not in [RolEnum.ADMINISTRADOR, RolEnum.COORDINADOR]:
        raise HTTPException(status_code=403, detail="Solo coordinadores pueden asignar evaluadores")
    
    # Verificar que el expediente existe
    exp = db.query(Expediente).filter(Expediente.id == expediente_id).first()
    if not exp:
        raise HTTPException(status_code=404, detail="Expediente no encontrado")
    
    # Verificar que el evaluador existe y tiene rol de evaluador
    evaluador = db.query(User).filter(User.id == evaluador_id).first()
    if not evaluador:
        raise HTTPException(status_code=404, detail="Evaluador no encontrado")
    
    if evaluador.rol != RolEnum.EVALUADOR:
        raise HTTPException(status_code=400, detail="El usuario no tiene rol de evaluador")
    
    if not evaluador.activo:
        raise HTTPException(status_code=400, detail="El evaluador no está activo")
    
    # Verificar si ya existe evaluación para este evaluador en este expediente
    evaluacion_existente = db.query(Evaluacion).filter(
        Evaluacion.expediente_id == expediente_id,
        Evaluacion.evaluador_id == evaluador_id
    ).first()
    
    if evaluacion_existente:
        raise HTTPException(status_code=400, detail="Este evaluador ya está asignado a este expediente")
    
    # Un solo evaluador por expediente (modelo de evaluación única con rúbrica).
    evaluadores_actuales = db.query(Evaluacion).filter(Evaluacion.expediente_id == expediente_id).all()
    if len(evaluadores_actuales) >= 1:
        raise HTTPException(status_code=400, detail="Este expediente ya tiene un evaluador asignado")
    
    # Crear nueva evaluación
    nueva_evaluacion = Evaluacion(
        expediente_id=expediente_id,
        evaluador_id=evaluador_id,
        fecha_asignacion=datetime.utcnow()
    )
    db.add(nueva_evaluacion)
    
    # Crear notificación para el evaluador
    notificacion = Notificacion(
        usuario_id=evaluador_id,
        expediente_id=expediente_id,
        titulo="Nueva evaluación asignada",
        mensaje=f"Se te ha asignado la evaluación del expediente: {exp.codigo_unico} - {exp.titulo_protocolo}"
    )
    db.add(notificacion)
    
    db.commit()
    db.refresh(nueva_evaluacion)
    
    return {
        "message": "Evaluador asignado exitosamente",
        "evaluacion_id": nueva_evaluacion.id,
        "evaluador": {"id": evaluador.id, "nombre": evaluador.nombre, "apellido": evaluador.apellido},
        "expediente_codigo": exp.codigo_unico
    }