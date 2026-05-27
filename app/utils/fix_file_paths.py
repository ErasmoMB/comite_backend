"""
Script de diagnosis y reparación de rutas de archivos

Usa:
    python -m app.utils.fix_file_paths --check      # Solo diagnosticar
    python -m app.utils.fix_file_paths --fix        # Reparar
"""

import sys
from pathlib import Path
from sqlalchemy.orm import Session
from app.db.database import SessionLocal, engine
from app.models import Documento, Dictamen
from app.utils.file_utils import get_upload_dir, get_relative_upload_path, resolve_file_path


def check_files(db: Session):
    """Verifica el estado de todas las rutas de archivos"""
    print("\n" + "="*70)
    print("DIAGNOSIS DE RUTAS DE ARCHIVOS")
    print("="*70 + "\n")
    
    documentos = db.query(Documento).all()
    dictamenes = db.query(Dictamen).all()
    
    uploads_base = get_upload_dir()
    print(f"📁 Directorio base de uploads: {uploads_base}\n")
    
    # Revisar documentos
    print("📄 DOCUMENTOS")
    print("-" * 70)
    docs_perdidos = 0
    docs_ok = 0
    
    for doc in documentos:
        if not doc.ruta_archivo:
            print(f"  ⚠️  ID {doc.id}: sin ruta asignada")
            docs_perdidos += 1
            continue
        
        file_path = resolve_file_path(doc.ruta_archivo)
        if file_path:
            print(f"  ✅ ID {doc.id}: {doc.nombre_archivo} (ruta OK)")
            docs_ok += 1
        else:
            print(f"  ❌ ID {doc.id}: {doc.nombre_archivo}")
            print(f"     Ruta en BD: {doc.ruta_archivo}")
            print(f"     Archivo no encontrado")
            docs_perdidos += 1
    
    print(f"\nResumen: {docs_ok} OK, {docs_perdidos} perdidos\n")
    
    # Revisar PDFs de dictamenes
    print("📋 DICTAMENES (PDFs)")
    print("-" * 70)
    pdfs_perdidos = 0
    pdfs_ok = 0
    
    for dic in dictamenes:
        if not dic.archivo_url:
            continue
        
        file_path = resolve_file_path(dic.archivo_url)
        if file_path:
            print(f"  ✅ ID {dic.id}: {dic.numero_dictamen} (PDF OK)")
            pdfs_ok += 1
        else:
            print(f"  ❌ ID {dic.id}: {dic.numero_dictamen}")
            print(f"     Ruta en BD: {dic.archivo_url}")
            print(f"     PDF no encontrado")
            pdfs_perdidos += 1
    
    print(f"\nResumen: {pdfs_ok} OK, {pdfs_perdidos} perdidos\n")
    
    return {
        "documentos": {"ok": docs_ok, "perdidos": docs_perdidos},
        "dictamenes": {"ok": pdfs_ok, "perdidos": pdfs_perdidos},
    }


def fix_paths(db: Session):
    """Intenta reparar las rutas de archivos"""
    print("\n" + "="*70)
    print("REPARACIÓN DE RUTAS DE ARCHIVOS")
    print("="*70 + "\n")
    
    uploads_base = get_upload_dir()
    
    # Buscar archivos perdidos en el filesystem
    print("🔍 Buscando archivos huérfanos en uploads/...\n")
    
    documentos = db.query(Documento).all()
    huerfanos = []
    
    # Listar todos los archivos que existen
    for expediente_dir in uploads_base.glob("*"):
        if expediente_dir.is_dir():
            for archivo in expediente_dir.glob("*"):
                if archivo.is_file():
                    relative_path = get_relative_upload_path(archivo)
                    
                    # Buscar si existe en BD
                    encontrado = any(
                        doc.ruta_archivo and relative_path in doc.ruta_archivo
                        for doc in documentos
                    )
                    
                    if not encontrado:
                        huerfanos.append((archivo, relative_path))
    
    if huerfanos:
        print(f"  Encontrados {len(huerfanos)} archivos sin referencia en BD:")
        for archivo, relative_path in huerfanos[:10]:
            print(f"    - {relative_path} ({archivo.stat().st_size} bytes)")
    else:
        print("  ✅ No hay archivos huérfanos\n")
    
    # Intentar normalizar rutas
    print("\n🔧 Normalizando rutas en BD...\n")
    actualizados = 0
    
    for doc in documentos:
        if not doc.ruta_archivo:
            continue
        
        # Resolver la ruta
        file_path = resolve_file_path(doc.ruta_archivo)
        if file_path:
            relative_path = get_relative_upload_path(file_path)
            if relative_path != doc.ruta_archivo:
                print(f"  📝 ID {doc.id}: actualizando ruta")
                print(f"     De: {doc.ruta_archivo}")
                print(f"     A:  {relative_path}")
                doc.ruta_archivo = relative_path
                actualizados += 1
    
    if actualizados > 0:
        db.commit()
        print(f"\n✅ {actualizados} rutas actualizadas en BD\n")
    else:
        print("  ℹ️  No hay rutas que actualizar\n")


if __name__ == "__main__":
    db = SessionLocal()
    
    try:
        if len(sys.argv) > 1:
            if sys.argv[1] == "--check":
                check_files(db)
            elif sys.argv[1] == "--fix":
                check_files(db)
                print("\n" + "="*70 + "\n")
                fix_paths(db)
            else:
                print("Uso: python fix_file_paths.py [--check|--fix]")
        else:
            check_files(db)
    finally:
        db.close()
