from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

class UserBase(BaseModel):
    email: Optional[EmailStr] = None
    correo: Optional[EmailStr] = None
    nombre: Optional[str] = None
    apellido: Optional[str] = None
    nombres: Optional[str] = None
    apellidos: Optional[str] = None

class UserCreate(UserBase):
    password: str
    rol: str = "investigador"
    especialidad: Optional[str] = None
    carga_trabajo: Optional[int] = None
    conflicto_interes: bool = False
    # Datos académicos del registro público (según rol)
    codigo_estudiante: Optional[str] = None
    laboratorio: Optional[str] = None

class AdminUserCreate(BaseModel):
    """Alta de usuario hecha por el administrador (cualquier rol, incl. internos)."""
    email: EmailStr
    password: str
    nombre: str
    apellido: str
    rol: str
    especialidad: Optional[str] = None
    carga_trabajo: Optional[int] = None
    conflicto_interes: bool = False

class UserUpdate(BaseModel):
    nombre: Optional[str] = None
    apellido: Optional[str] = None
    rol: Optional[str] = None
    activo: Optional[bool] = None

class UserResponse(BaseModel):
    id: int
    email: EmailStr
    nombre: str
    apellido: str
    rol: str
    activo: bool = True
    especialidad: Optional[str] = None
    carga_trabajo: Optional[int] = None
    conflicto_interes: bool = False
    codigo_estudiante: Optional[str] = None
    laboratorio: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class LoginRequest(BaseModel):
    correo: EmailStr
    rol: str
    password: str


class LoginResponse(BaseModel):
    usuario: UserResponse
    redirectTo: str

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    user_id: Optional[int] = None


class AutorBase(BaseModel):
    apellidos_nombres: str
    codigo_estudiante: Optional[str] = None
    correo: Optional[str] = None
    telefono: Optional[str] = None

class AutorResponse(AutorBase):
    id: int
    orden: int
    es_principal: bool

    class Config:
        from_attributes = True


class ExpedienteBase(BaseModel):
    titulo_protocolo: str
    tipo_tramite: Optional[str] = "proyecto_nuevo"
    facultad: Optional[str] = None
    # Flujo dinámico (Fase 1). modalidad se deriva del rol en el backend.
    programa_estudios: Optional[str] = None
    ciclo: Optional[str] = None
    nivel_posgrado: Optional[str] = None

class ExpedienteCreate(ExpedienteBase):
    autores: List[AutorBase] = []

class CambioTituloCreate(BaseModel):
    proyecto_origen_id: int
    numero_acta: str
    programa_estudios: str
    ciclo: str
    titulo_nuevo: str
    autores: List[AutorBase] = []

class ExpedienteUpdate(BaseModel):
    titulo_protocolo: Optional[str] = None
    tipo_tramite: Optional[str] = None
    facultad: Optional[str] = None
    estado: Optional[str] = None
    programa_estudios: Optional[str] = None
    ciclo: Optional[str] = None
    nivel_posgrado: Optional[str] = None
    autores: Optional[List[AutorBase]] = None

class ExpedienteResponse(ExpedienteBase):
    id: int
    codigo_unico: Optional[str]
    investigador_id: int
    modalidad: Optional[str] = None
    estado: str
    fecha_envio: Optional[datetime]
    numero_acta: Optional[str] = None
    titulo_anterior: Optional[str] = None
    titulo_nuevo: Optional[str] = None
    autores: List[AutorResponse] = []
    created_at: datetime = Field(validation_alias="fecha_creacion")

    class Config:
        from_attributes = True


class DocumentoBase(BaseModel):
    nombre_archivo: str
    tipo_documento: str
    es_obligatorio: bool = True

class DocumentoResponse(DocumentoBase):
    id: int
    validado: bool
    version: int
    ruta_archivo: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class CriterioRubricaItem(BaseModel):
    key: str
    nombre: str
    descripcion: str
    puntaje_max: int

class RubricaResponse(BaseModel):
    criterios: List[CriterioRubricaItem]
    puntaje_total_max: int
    umbrales: dict

class CriterioEvaluacionInput(BaseModel):
    key: str
    puntaje: int
    observacion: Optional[str] = None

class CriterioEvaluacionResponse(BaseModel):
    criterio_key: str
    puntaje: int
    observacion: Optional[str] = None

    class Config:
        from_attributes = True

class EvaluacionBase(BaseModel):
    pass

class EvaluacionCreate(EvaluacionBase):
    expediente_id: int

class EvaluacionUpdate(BaseModel):
    recommendation: Optional[str] = None
    observaciones: Optional[str] = None
    completa: Optional[bool] = None
    criterios: Optional[List[CriterioEvaluacionInput]] = None

class EvaluacionAsignarRequest(BaseModel):
    evaluador_id: int

class EvaluacionResponse(EvaluacionBase):
    id: int
    expediente_id: int
    evaluador_id: int
    recommendation: Optional[str]
    observaciones: Optional[str]
    completa: bool
    conflicto_interes: bool
    titulo_protocolo: Optional[str] = None
    criterios: List[CriterioEvaluacionResponse] = []
    puntaje_total: Optional[int] = None
    resultado: Optional[str] = None
    created_at: datetime = Field(validation_alias="fecha_asignacion")

    class Config:
        from_attributes = True


class DictamenBase(BaseModel):
    contenido: str

class DictamenCreate(DictamenBase):
    expediente_id: int

class DictamenUpdate(BaseModel):
    contenido: Optional[str] = None
    firmado: Optional[bool] = None

class DictamenResponse(DictamenBase):
    id: int
    expediente_id: int
    numero_dictamen: Optional[str]
    tipo_dictamen: Optional[str]
    firmado: bool
    fecha_emision: Optional[datetime] = None
    fecha_firma: Optional[datetime] = None
    archivo_url: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class NotificacionBase(BaseModel):
    titulo: str
    mensaje: str
    expediente_id: Optional[int] = None

class NotificacionCreate(NotificacionBase):
    usuario_id: int

class NotificacionUpdate(BaseModel):
    leida: Optional[bool] = None

class NotificacionResponse(NotificacionBase):
    id: int
    usuario_id: int
    leida: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ==================== SUBSANACIÓN ====================
class SubsanacionRequest(BaseModel):
    observaciones: str
    documentos_respuesta: Optional[List[str]] = None

class SubsanacionResponse(BaseModel):
    mensaje: str
    expediente_id: int
    estado: str
    fecha_subsanacion: datetime


# ==================== IA - SCHEMAS CLAROS ====================
class IAAnalisisResponse(BaseModel):
    """Respuesta de análisis de IA para expediente"""
    analisis: str
    recomendaciones: List[str]
    confianza: float  # 0-100
    factores_clave: Optional[List[str]] = None

class IAInconsistenciasResponse(BaseModel):
    """Respuesta de detección de inconsistencias"""
    inconsistencias: List[Dict[str, Any]]
    cantidad: int
    mensaje: str


# ==================== REPORTES - SCHEMAS CLAROS ====================
class EstadisticasExpediente(BaseModel):
    total: int
    por_estado: Dict[str, int]

class EstadisticasEvaluadores(BaseModel):
    total_evaluadores: int
    carga_promedio: float
    carga_maxima: int

class ReporteTiempoAtencion(BaseModel):
    expediente_id: int
    codigo: str
    dias: int
    estado: str

class ReporteCargaEvaluadores(BaseModel):
    evaluador_id: int
    nombre: Optional[str]
    total_evaluaciones: int

class ReporteResultados(BaseModel):
    tipo: str
    total: int

class ReporteGeneralResponse(BaseModel):
    """Reporte general del sistema"""
    fecha_generacion: datetime
    expedientes: EstadisticasExpediente
    evaluadores: EstadisticasEvaluadores
    tiempos_atencion: List[ReporteTiempoAtencion]
    carga_evaluadores: List[ReporteCargaEvaluadores]
    resultados: List[ReporteResultados]
    archivo_url: Optional[str] = None