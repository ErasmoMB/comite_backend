"""Sirve las plantillas y guías oficiales del Comité (públicas, sin auth)."""
import mimetypes
from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse

from app.core.config import BASE_DIR

router = APIRouter()

PLANTILLAS_DIR = BASE_DIR / "plantillas"

# key -> (archivo en disco, nombre amigable para descargar)
PLANTILLAS = {
    "solicitud_evaluacion": ("solicitud_evaluacion.docx", "Plantilla - Solicitud de evaluacion.docx"),
    "carta_aprobacion": ("carta_aprobacion.docx", "Plantilla - Carta de aprobacion del docente.docx"),
    "guia_pago": ("guia_pago.png", "Guia de pago - ERP.png"),
    "estructura_nombres": ("estructura_nombres.pdf", "Estructura del nombre de los archivos.pdf"),
    "cambio_titulo": ("cambio_titulo.docx", "Formato - Solicitud de cambio de titulo.docx"),
}


@router.get("/{key}")
def get_plantilla(key: str, modo: str = Query("ver", pattern="^(ver|descargar)$")):
    item = PLANTILLAS.get(key)
    if not item:
        raise HTTPException(status_code=404, detail="Plantilla no encontrada")
    archivo, nombre_descarga = item
    path = PLANTILLAS_DIR / archivo
    if not path.exists():
        raise HTTPException(status_code=404, detail="El archivo de la plantilla no está disponible.")

    content_type = mimetypes.guess_type(archivo)[0] or "application/octet-stream"
    disposition = "attachment" if modo == "descargar" else "inline"
    nombre_utf8 = quote(nombre_descarga)
    headers = {
        "Content-Disposition": f"{disposition}; filename*=UTF-8''{nombre_utf8}",
        "Access-Control-Expose-Headers": "Content-Disposition",
    }
    return FileResponse(path, media_type=content_type, headers=headers)
