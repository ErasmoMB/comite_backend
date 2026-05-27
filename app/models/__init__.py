from sqlalchemy.orm import relationship
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.sql import func
from app.db.database import Base
import enum

class RolEnum(str, enum.Enum):
    ADMINISTRADOR = "administrador"
    COORDINADOR = "coordinador"
    SECRETARIA = "secretaria"
    INVESTIGADOR = "investigador"
    EVALUADOR = "evaluador"
    ESTUDIANTE = "estudiante"

class EstadoExpedienteEnum(str, enum.Enum):
    BORRADOR = "borrador"
    ENVIADO = "enviado"
    EN_REVISION = "en_revision"
    SUBSANACION = "subsanacion"
    APROBADO = "aprobado"
    ARCHIVADO = "archivado"

class TipoDictamenEnum(str, enum.Enum):
    """Estados permitidos para dictamen: solo APROBADO u OBSERVADO"""
    APROBADO = "aprobado"
    OBSERVADO = "observado"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    nombre = Column(String(255), nullable=False)
    apellido = Column(String(255), nullable=False)
    rol = Column(String(50), nullable=False, default="investigador")
    activo = Column(Boolean, default=True)
    especialidad = Column(String(255), nullable=True)
    carga_trabajo = Column(Integer, nullable=True)
    conflicto_interes = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

    expedientes = relationship("Expediente", back_populates="investigador")
    evaluaciones = relationship("Evaluacion", back_populates="evaluador")
    notificaciones = relationship("Notificacion", back_populates="usuario")


class Expediente(Base):
    __tablename__ = "expedientes"

    id = Column(Integer, primary_key=True, index=True)
    codigo_unico = Column(String(50), unique=True, index=True)
    titulo_protocolo = Column(Text, nullable=False)
    investigador_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    tipo_tramite = Column(String(100), nullable=True)
    facultad = Column(String(255), nullable=True)
    prioridad = Column(String(50), default="normal", nullable=False)
    estado = Column(String(50), default="borrador")
    fecha_envio = Column(DateTime, nullable=True)
    fecha_creacion = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

    investigador = relationship("User", back_populates="expedientes")
    documentos = relationship("Documento", back_populates="expediente")
    evaluaciones = relationship("Evaluacion", back_populates="expediente")
    dictamines = relationship("Dictamen", back_populates="expediente")
    notificaciones = relationship("Notificacion", back_populates="expediente")
    bitacora = relationship("Bitacora", back_populates="expediente")
    historial = relationship("HistorialExpediente", back_populates="expediente")


class Documento(Base):
    __tablename__ = "documentos"

    id = Column(Integer, primary_key=True, index=True)
    expediente_id = Column(Integer, ForeignKey("expedientes.id"), nullable=False)
    nombre_archivo = Column(String(255), nullable=False)
    tipo_documento = Column(String(100), nullable=False)
    ruta_archivo = Column(String(500))
    version = Column(Integer, default=1)
    es_obligatorio = Column(Boolean, default=True)
    validado = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())

    expediente = relationship("Expediente", back_populates="documentos")


class Evaluacion(Base):
    __tablename__ = "evaluaciones"

    id = Column(Integer, primary_key=True, index=True)
    expediente_id = Column(Integer, ForeignKey("expedientes.id"), nullable=False)
    evaluador_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    nivel_riesgo = Column(String(50))
    recommendation = Column(Text)
    observaciones = Column(Text)
    completa = Column(Boolean, default=False)
    conflicto_interes = Column(Boolean, default=False)
    fecha_asignacion = Column(DateTime, server_default=func.now())
    fecha_envio = Column(DateTime, nullable=True)

    expediente = relationship("Expediente", back_populates="evaluaciones")
    evaluador = relationship("User", back_populates="evaluaciones")

    @property
    def titulo_protocolo(self):
        """Propiedad para acceder al título del protocolo del expediente asociado"""
        if self.expediente:
            return self.expediente.titulo_protocolo
        return None


class Dictamen(Base):
    __tablename__ = "dictamines"

    id = Column(Integer, primary_key=True, index=True)
    expediente_id = Column(Integer, ForeignKey("expedientes.id"), nullable=False)
    numero_dictamen = Column(String(50), unique=True)
    tipo_dictamen = Column(String(50))
    contenido = Column(Text)
    fecha_emision = Column(DateTime, nullable=True)
    fecha_firma = Column(DateTime, nullable=True)
    firmado = Column(Boolean, default=False)
    archivo_url = Column(String(255), nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    expediente = relationship("Expediente", back_populates="dictamines")


class Notificacion(Base):
    __tablename__ = "notificaciones"

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    expediente_id = Column(Integer, ForeignKey("expedientes.id"), nullable=True)
    titulo = Column(String(255), nullable=False)
    mensaje = Column(Text, nullable=False)
    leida = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())

    usuario = relationship("User", back_populates="notificaciones")
    expediente = relationship("Expediente", back_populates="notificaciones")


class Bitacora(Base):
    __tablename__ = "bitacora"

    id = Column(Integer, primary_key=True, index=True)
    expediente_id = Column(Integer, ForeignKey("expedientes.id"), nullable=False)
    accion = Column(String(255), nullable=False)
    detalle = Column(Text)
    usuario_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    expediente = relationship("Expediente", back_populates="bitacora")


class HistorialExpediente(Base):
    __tablename__ = "historial_expediente"

    id = Column(Integer, primary_key=True, index=True)
    expediente_id = Column(Integer, ForeignKey("expedientes.id"), nullable=False)
    estado_anterior = Column(String(50))
    estado_nuevo = Column(String(50))
    observaciones = Column(Text)
    created_at = Column(DateTime, server_default=func.now())

    expediente = relationship("Expediente", back_populates="historial")