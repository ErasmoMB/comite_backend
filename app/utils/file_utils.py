"""Utilidades para manejo de archivos y rutas"""
from pathlib import Path
from typing import Optional
import os

def get_upload_dir(subdirectory: str = "") -> Path:
    """
    Obtiene el directorio de uploads absoluto.
    
    Usa la variable de entorno UPLOAD_DIR si está disponible,
    sino usa la ruta relativa basada en el directorio actual del script.
    
    Args:
        subdirectory: Subdirectorio dentro de uploads (ej: "dictamenes", "1", etc)
    
    Returns:
        Path absoluto del directorio
    """
    base_upload_dir = os.getenv("UPLOAD_DIR")
    
    if base_upload_dir:
        # Usar variable de entorno si existe
        upload_dir = Path(base_upload_dir)
    else:
        # Usar ruta relativa desde el directorio raíz del proyecto
        # Busca hacia arriba hasta encontrar app/
        current_dir = Path(__file__).parent.parent.parent  # app/utils/file_utils.py -> proyecto/
        upload_dir = current_dir / "uploads"
    
    # Crear subdirectorio si se proporciona
    if subdirectory:
        upload_dir = upload_dir / subdirectory
    
    # Crear directorio si no existe
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    # Retornar como ruta absoluta
    return upload_dir.resolve()

def get_relative_upload_path(absolute_path: Path) -> str:
    """
    Convierte una ruta absoluta a ruta relativa desde uploads.
    
    Args:
        absolute_path: Ruta absoluta del archivo
    
    Returns:
        Ruta relativa desde la carpeta uploads (ej: "1/archivo_abc123.pdf")
    """
    uploads_base = get_upload_dir()
    try:
        relative = absolute_path.relative_to(uploads_base)
        # Convertir a string con separadores / para compatibilidad cross-platform
        return str(relative).replace("\\", "/")
    except ValueError:
        # Si la ruta no está dentro de uploads, retornarla como está
        return str(absolute_path)

def resolve_file_path(relative_or_absolute_path: str) -> Optional[Path]:
    """
    Resuelve una ruta que puede ser relativa o absoluta a un archivo real.
    
    Args:
        relative_or_absolute_path: Ruta relativa desde uploads o ruta absoluta
    
    Returns:
        Path absoluto del archivo si existe, None si no existe
    """
    path = Path(relative_or_absolute_path)
    
    # Si ya es absoluta y existe, retornarla
    if path.is_absolute() and path.exists():
        return path
    
    # Si es relativa, buscarla dentro de uploads
    if not path.is_absolute():
        uploads_base = get_upload_dir()
        full_path = (uploads_base / path).resolve()
        if full_path.exists():
            return full_path
    
    return None
