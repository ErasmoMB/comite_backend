import os

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

# --- Candado: este proyecto SIEMPRE trabaja contra la base de Aiven (PostgreSQL). ---
# El fallback a SQLite local (config.py) solo debe usarse para tests aislados, y
# únicamente si se pide de forma explícita con ALLOW_SQLITE=1. Así evitamos que un
# .env faltante o mal configurado haga arrancar el backend con la base equivocada.
_ALLOW_SQLITE = os.getenv("ALLOW_SQLITE", "").strip().lower() in ("1", "true", "yes")
if settings.DATABASE_URL.startswith("sqlite") and not _ALLOW_SQLITE:
    raise RuntimeError(
        "DATABASE_URL apunta a SQLite local, pero este proyecto SIEMPRE debe usar la "
        "base de Aiven (PostgreSQL).\n"
        "  → Configura backend/.env con la DATABASE_URL de Aiven (postgresql://...).\n"
        "  → Si de verdad necesitas SQLite para tests aislados, exporta ALLOW_SQLITE=1.\n"
        f"  DATABASE_URL actual: {settings.DATABASE_URL}"
    )

# Log de arranque: deja claro contra qué base se conecta (sin exponer credenciales).
_db_host = settings.DATABASE_URL.split("@")[-1].split("?")[0] if "@" in settings.DATABASE_URL else settings.DATABASE_URL
print(f"[DB] Conectado a: {_db_host}", flush=True)

engine_kwargs = {"pool_pre_ping": True}
if settings.DATABASE_URL.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}

engine = create_engine(settings.DATABASE_URL, **engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    import app.models
    Base.metadata.create_all(bind=engine)