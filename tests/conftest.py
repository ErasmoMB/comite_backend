import os
# Forzar SQLite en memoria ANTES de importar la app (evita conectar a Aiven).
os.environ["DATABASE_URL"] = "sqlite://"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.database import Base, get_db
from app.api.auth.routes import get_current_user
from app.main import app
import app.models as models  # noqa: F401  (registra todos los modelos en Base)

engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture
def db():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(db):
    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


def make_user(db, rol, email=None):
    """Crea y persiste un usuario con el rol dado."""
    user = models.User(
        email=email or f"{rol}@test.com",
        password_hash="x",
        nombre="Test",
        apellido=rol,
        rol=rol,
        activo=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def auth_as(user):
    """Devuelve un override de get_current_user que retorna `user`."""
    def _override():
        return user
    return _override
