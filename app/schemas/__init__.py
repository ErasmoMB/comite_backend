from pydantic import BaseModel, EmailStr, Field
from typing import Optional
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


class ExpedienteBase(BaseModel):
    titulo_protocolo: str

class ExpedienteCreate(ExpedienteBase):
    pass

class ExpedienteUpdate(BaseModel):
    titulo_protocolo: Optional[str] = None
    estado: Optional[str] = None

class ExpedienteResponse(ExpedienteBase):
    id: int
    codigo_unico: Optional[str]
    investigador_id: int
    estado: str
    fecha_envio: Optional[datetime]
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
    created_at: datetime

    class Config:
        from_attributes = True


class EvaluacionBase(BaseModel):
    pass

class EvaluacionCreate(EvaluacionBase):
    expediente_id: int

class EvaluacionUpdate(BaseModel):
    nivel_riesgo: Optional[str] = None
    recommendation: Optional[str] = None
    observaciones: Optional[str] = None
    completa: Optional[bool] = None

class EvaluacionResponse(EvaluacionBase):
    id: int
    expediente_id: int
    evaluador_id: int
    nivel_riesgo: Optional[str]
    observaciones: Optional[str]
    completa: bool
    conflicto_interes: bool
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