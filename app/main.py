from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.db.database import engine, Base, init_db
from app import models

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

init_db()

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_HOSTS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.api.auth import routes as auth
from app.api.users import routes as users
from app.api.expedientes import routes as expedientes
from app.api.evaluacion import routes as evaluacion
from app.api.dictamen import routes as dictamen
from app.api.notificaciones import routes as notificaciones
from app.api.reportes import routes as reportes
from app.api.ia import routes as ia

app.include_router(auth.router, prefix=f"{settings.API_V1_STR}/auth", tags=["auth"])
app.include_router(users.router, prefix=f"{settings.API_V1_STR}/users", tags=["users"])
app.include_router(expedientes.router, prefix=f"{settings.API_V1_STR}/expedientes", tags=["expedientes"])
app.include_router(evaluacion.router, prefix=f"{settings.API_V1_STR}/evaluacion", tags=["evaluacion"])
app.include_router(dictamen.router, prefix=f"{settings.API_V1_STR}/dictamen", tags=["dictamen"])
app.include_router(notificaciones.router, prefix=f"{settings.API_V1_STR}/notificaciones", tags=["notificaciones"])
app.include_router(reportes.router, prefix=f"{settings.API_V1_STR}/reportes", tags=["reportes"])
app.include_router(ia.router, prefix=f"{settings.API_V1_STR}/ia", tags=["ia"])

@app.get("/")
def root():
    return {"message": "API Comité de Ética", "status": "running"}

@app.get(f"{settings.API_V1_STR}/health")
def health_check():
    return {"status": "healthy"}