"""Chat 1-a-1 entre solicitantes y la Secretaría del Comité (bandeja compartida del rol).

Un hilo por solicitante (`MensajeChat.solicitante_id`). Ver spec:
docs/superpowers/specs/2026-07-02-chat-secretaria-design.md

OJO: las rutas fijas (/conversaciones, /solicitantes, /mios, /no-leidos) van ANTES
de /{solicitante_id} para que no las capture la ruta dinámica.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session
from typing import List

from app.db.database import get_db
from app.models import User, RolEnum, MensajeChat, ROLES_AUTO_REGISTRO
from app.schemas import (
    MensajeChatCreate, MensajeChatResponse, ConversacionResumen, SolicitanteChatItem,
)
from app.api.auth.routes import get_current_user

router = APIRouter()

TEXTO_MAX = 2000

# La secretaría comparte bandeja; el admin también puede atenderla.
ROLES_SECRETARIA = {RolEnum.SECRETARIA.value, RolEnum.ADMINISTRADOR.value}


def _rol(user: User) -> str:
    return user.rol.value if hasattr(user.rol, "value") else user.rol


def _exigir_solicitante(user: User):
    if _rol(user) not in ROLES_AUTO_REGISTRO:
        raise HTTPException(status_code=403, detail="Solo los solicitantes pueden usar este chat")


def _exigir_secretaria(user: User):
    if _rol(user) not in ROLES_SECRETARIA:
        raise HTTPException(status_code=403, detail="Solo la secretaría puede acceder a la bandeja de chat")


def _validar_texto(texto: str) -> str:
    texto = (texto or "").strip()
    if not texto:
        raise HTTPException(status_code=400, detail="El mensaje no puede estar vacío")
    if len(texto) > TEXTO_MAX:
        raise HTTPException(status_code=400, detail=f"El mensaje no puede superar {TEXTO_MAX} caracteres")
    return texto


def _get_solicitante(db: Session, solicitante_id: int) -> User:
    solicitante = db.query(User).filter(User.id == solicitante_id).first()
    if not solicitante or _rol(solicitante) not in ROLES_AUTO_REGISTRO:
        raise HTTPException(status_code=404, detail="Solicitante no encontrado")
    return solicitante


# ---------- Lado solicitante (rutas fijas) ----------

@router.get("/mios", response_model=List[MensajeChatResponse])
def get_mis_mensajes(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Hilo del solicitante autenticado. Abrirlo marca como leídos los mensajes de secretaría."""
    _exigir_solicitante(current_user)
    db.query(MensajeChat).filter(
        MensajeChat.solicitante_id == current_user.id,
        MensajeChat.autor_id != current_user.id,
        MensajeChat.leido == False,
    ).update({"leido": True}, synchronize_session=False)
    db.commit()
    return (
        db.query(MensajeChat)
        .filter(MensajeChat.solicitante_id == current_user.id)
        .order_by(MensajeChat.created_at.asc(), MensajeChat.id.asc())
        .all()
    )


@router.post("/mios", response_model=MensajeChatResponse)
def enviar_mensaje_solicitante(payload: MensajeChatCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _exigir_solicitante(current_user)
    texto = _validar_texto(payload.texto)
    mensaje = MensajeChat(solicitante_id=current_user.id, autor_id=current_user.id, texto=texto)
    db.add(mensaje)
    db.commit()
    db.refresh(mensaje)
    return mensaje


@router.get("/mios/no-leidos")
def mis_no_leidos(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Mensajes de secretaría que el solicitante aún no ha visto (para el badge)."""
    _exigir_solicitante(current_user)
    count = db.query(MensajeChat).filter(
        MensajeChat.solicitante_id == current_user.id,
        MensajeChat.autor_id != current_user.id,
        MensajeChat.leido == False,
    ).count()
    return {"no_leidos": count}


# ---------- Lado secretaría (rutas fijas) ----------

@router.get("/conversaciones", response_model=List[ConversacionResumen])
def get_conversaciones(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Bandeja: una entrada por solicitante con mensajes, ordenada por actividad reciente."""
    _exigir_secretaria(current_user)

    hilos = (
        db.query(
            MensajeChat.solicitante_id,
            func.max(MensajeChat.id).label("ultimo_id"),
        )
        .group_by(MensajeChat.solicitante_id)
        .all()
    )
    if not hilos:
        return []

    ultimos_ids = [h.ultimo_id for h in hilos]
    ultimos = {
        m.solicitante_id: m
        for m in db.query(MensajeChat).filter(MensajeChat.id.in_(ultimos_ids)).all()
    }

    # No leídos por hilo = mensajes escritos por el solicitante que secretaría no ha visto.
    no_leidos = dict(
        db.query(MensajeChat.solicitante_id, func.count(MensajeChat.id))
        .filter(MensajeChat.autor_id == MensajeChat.solicitante_id, MensajeChat.leido == False)
        .group_by(MensajeChat.solicitante_id)
        .all()
    )

    solicitantes = {
        u.id: u
        for u in db.query(User).filter(User.id.in_(list(ultimos.keys()))).all()
    }

    resumen = []
    for sid, mensaje in ultimos.items():
        u = solicitantes.get(sid)
        if not u:
            continue
        resumen.append(ConversacionResumen(
            solicitante_id=sid,
            nombre=f"{u.nombre} {u.apellido}".strip(),
            rol=_rol(u),
            email=u.email,
            codigo_estudiante=u.codigo_estudiante,
            ultimo_mensaje=mensaje.texto,
            ultima_fecha=mensaje.created_at,
            no_leidos=no_leidos.get(sid, 0),
        ))
    # El id del último mensaje desempata fechas idénticas (mismo segundo).
    resumen.sort(key=lambda c: ultimos[c.solicitante_id].id, reverse=True)
    return resumen


@router.get("/solicitantes", response_model=List[SolicitanteChatItem])
def get_solicitantes(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Todos los solicitantes registrados (para que secretaría inicie una conversación)."""
    _exigir_secretaria(current_user)
    usuarios = (
        db.query(User)
        .filter(User.rol.in_(list(ROLES_AUTO_REGISTRO)), User.activo == True)
        .order_by(User.apellido.asc(), User.nombre.asc())
        .all()
    )
    return [
        SolicitanteChatItem(
            id=u.id,
            nombre=f"{u.nombre} {u.apellido}".strip(),
            rol=_rol(u),
            email=u.email,
            codigo_estudiante=u.codigo_estudiante,
        )
        for u in usuarios
    ]


@router.get("/no-leidos")
def total_no_leidos(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Total de mensajes de solicitantes sin leer (badge de la bandeja)."""
    _exigir_secretaria(current_user)
    count = db.query(MensajeChat).filter(
        MensajeChat.autor_id == MensajeChat.solicitante_id,
        MensajeChat.leido == False,
    ).count()
    return {"no_leidos": count}


# ---------- Lado secretaría (rutas dinámicas, SIEMPRE al final) ----------

@router.get("/{solicitante_id}", response_model=List[MensajeChatResponse])
def get_hilo(solicitante_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Hilo de un solicitante. Abrirlo marca como leídos sus mensajes."""
    _exigir_secretaria(current_user)
    _get_solicitante(db, solicitante_id)
    db.query(MensajeChat).filter(
        MensajeChat.solicitante_id == solicitante_id,
        MensajeChat.autor_id == solicitante_id,
        MensajeChat.leido == False,
    ).update({"leido": True}, synchronize_session=False)
    db.commit()
    return (
        db.query(MensajeChat)
        .filter(MensajeChat.solicitante_id == solicitante_id)
        .order_by(MensajeChat.created_at.asc(), MensajeChat.id.asc())
        .all()
    )


@router.post("/{solicitante_id}", response_model=MensajeChatResponse)
def enviar_mensaje_secretaria(solicitante_id: int, payload: MensajeChatCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Responde (o inicia) la conversación con un solicitante."""
    _exigir_secretaria(current_user)
    _get_solicitante(db, solicitante_id)
    texto = _validar_texto(payload.texto)
    mensaje = MensajeChat(solicitante_id=solicitante_id, autor_id=current_user.id, texto=texto)
    db.add(mensaje)
    db.commit()
    db.refresh(mensaje)
    return mensaje
