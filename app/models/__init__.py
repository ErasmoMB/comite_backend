from sqlalchemy.orm import relationship
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.sql import func
from app.db.database import Base
import enum

class RolEnum(str, enum.Enum):
    # Roles internos: solo los crea el administrador (no se auto-registran)
    ADMINISTRADOR = "administrador"
    COORDINADOR = "coordinador"
    SECRETARIA = "secretaria"
    EVALUADOR = "evaluador"
    # Roles que SÍ pueden auto-registrarse desde el login público.
    # Son distintos a nivel de datos pero comparten la misma vista en el frontend.
    ESTUDIANTE_PREGRADO = "estudiante_pregrado"
    ESTUDIANTE_POSTGRADO = "estudiante_postgrado"
    INVESTIGADOR = "investigador"
    # Rol legado (datos antiguos). No usar en registros nuevos.
    ESTUDIANTE = "estudiante"


# Roles que un usuario puede elegir al auto-registrarse en /auth/register.
ROLES_AUTO_REGISTRO = {
    RolEnum.ESTUDIANTE_PREGRADO.value,
    RolEnum.ESTUDIANTE_POSTGRADO.value,
    RolEnum.INVESTIGADOR.value,
}

# Roles internos que únicamente el administrador puede crear.
ROLES_INTERNOS = {
    RolEnum.ADMINISTRADOR.value,
    RolEnum.COORDINADOR.value,
    RolEnum.SECRETARIA.value,
    RolEnum.EVALUADOR.value,
}

class EstadoExpedienteEnum(str, enum.Enum):
    BORRADOR = "borrador"
    ENVIADO = "enviado"
    EN_REVISION = "en_revision"
    SUBSANACION = "subsanacion"
    APROBADO = "aprobado"
    APROBADO_OBSERVACIONES = "aprobado_observaciones"
    NO_APROBADO = "no_aprobado"
    ARCHIVADO = "archivado"


class ModalidadEnum(str, enum.Enum):
    """Modalidad del expediente, derivada del rol del solicitante."""
    PREGRADO = "pregrado"
    POSTGRADO = "postgrado"
    INTERNO = "interno"


class TipoTramiteEnum(str, enum.Enum):
    PROYECTO_NUEVO = "proyecto_nuevo"
    CAMBIO_TITULO = "cambio_titulo"


# El rol con el que se inició sesión determina la modalidad del expediente.
ROL_A_MODALIDAD = {
    "estudiante_pregrado": ModalidadEnum.PREGRADO.value,
    "estudiante_postgrado": ModalidadEnum.POSTGRADO.value,
    "investigador": ModalidadEnum.INTERNO.value,
}

# Catálogos controlados (de los formularios oficiales del comité).
PROGRAMAS_ESTUDIOS = [
    "Enfermería",
    "Psicología",
    "Medicina Humana",
    "Farmacia y Bioquímica",
    "Nutrición y Dietética",
]
CICLOS = ["VII", "VIII", "IX", "X"]
# El cambio de título admite además "Egresado".
CICLOS_CAMBIO_TITULO = ["VII", "VIII", "IX", "X", "Egresado"]
NIVELES_POSGRADO = ["Segunda especialidad", "Maestría", "Doctorado"]

# Tipos de documento canónicos.
DOC_PROYECTO_PDF = "proyecto_pdf"
DOC_PROYECTO_WORD = "proyecto_word"
DOC_SOLICITUD_EVALUACION = "solicitud_evaluacion"
DOC_CARTA_APROBACION = "carta_aprobacion"
DOC_BOLETA_PAGO = "boleta_pago"
DOC_SOLICITUD_CAMBIO_TITULO = "solicitud_cambio_titulo"

# Etiquetas legibles para mostrar en el frontend.
DOCUMENTO_LABELS = {
    DOC_PROYECTO_PDF: "Proyecto de investigación (PDF)",
    DOC_PROYECTO_WORD: "Proyecto de investigación (Word)",
    DOC_SOLICITUD_EVALUACION: "Solicitud de evaluación por Comité de Ética (PDF)",
    DOC_CARTA_APROBACION: "Carta de aprobación del docente/asesor (PDF)",
    DOC_BOLETA_PAGO: "Boleta de pago del trámite (PDF o imagen)",
    DOC_SOLICITUD_CAMBIO_TITULO: "Solicitud de cambio de título (PDF)",
}

# Indicaciones (guía) que se muestran al usuario por cada documento.
DOCUMENTO_INDICACIONES = {
    DOC_PROYECTO_PDF: [
        "En formato PDF.",
        "Debe cumplir con la estructura establecida por la UCH.",
        "El formato y la estructura los proporciona el docente responsable de la asignatura.",
    ],
    DOC_PROYECTO_WORD: [
        "El mismo proyecto, en formato Word (editable).",
    ],
    DOC_SOLICITUD_EVALUACION: [
        "Dirigida al Presidente del Comité de Ética.",
        "Debidamente completada y firmada.",
        "En formato PDF.",
    ],
    DOC_CARTA_APROBACION: [
        "El docente/asesor declara que el proyecto es apto para pasar a evaluación ética.",
        "Debe estar firmada por el docente o asesor.",
        "En formato PDF.",
    ],
    DOC_BOLETA_PAGO: [
        "Concepto: “Evaluación de proyecto de tesis por Comité de Ética”.",
        "Descargada desde la Intranet (ERP).",
        "En formato PDF o imagen.",
    ],
    DOC_SOLICITUD_CAMBIO_TITULO: [
        "En formato PDF, debidamente firmada.",
        "Nombra el archivo: ACTA - NÚMERO CAMBIO DE TITULO (APELLIDO o APELLIDOS) – ESCUELA PROFESIONAL.",
    ],
}

# Plantilla/guía asociada a un documento (se sirve desde /plantillas/{key}).
#   accion = "descargar" (Word) | "ver" (PDF/imagen)
DOCUMENTO_PLANTILLA = {
    DOC_SOLICITUD_EVALUACION: {"key": "solicitud_evaluacion", "accion": "descargar", "label": "Descargar plantilla"},
    DOC_CARTA_APROBACION: {"key": "carta_aprobacion", "accion": "descargar", "label": "Descargar plantilla"},
    DOC_BOLETA_PAGO: {"key": "guia_pago", "accion": "ver", "label": "Ver guía de pago (ERP)"},
    DOC_SOLICITUD_CAMBIO_TITULO: {"key": "cambio_titulo", "accion": "descargar", "label": "Descargar formato (Word)"},
}

# Guía global sobre el nombre de los archivos (regla obligatoria del comité).
GUIA_NOMBRES = {
    "key": "estructura_nombres",
    "label": "Ver guía: estructura del nombre de los archivos",
    "texto": "Nombra cada archivo según la estructura del Comité de Ética. Los documentos que no cumplan la nomenclatura no serán considerados en la evaluación.",
}

# Formato permitido por tipo de documento (validación estricta en la subida).
_PDF = {"application/pdf"}
_WORD = {"application/msword", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"}
_IMG = {"image/png", "image/jpeg", "image/jpg", "image/webp"}
DOCUMENTO_FORMATOS = {
    DOC_PROYECTO_PDF: {"mimes": _PDF, "ext": {".pdf"}, "desc": "PDF"},
    DOC_PROYECTO_WORD: {"mimes": _WORD, "ext": {".doc", ".docx"}, "desc": "Word (.doc, .docx)"},
    DOC_SOLICITUD_EVALUACION: {"mimes": _PDF, "ext": {".pdf"}, "desc": "PDF"},
    DOC_CARTA_APROBACION: {"mimes": _PDF, "ext": {".pdf"}, "desc": "PDF"},
    DOC_BOLETA_PAGO: {"mimes": _PDF | _IMG, "ext": {".pdf", ".png", ".jpg", ".jpeg", ".webp"}, "desc": "PDF o imagen"},
    DOC_SOLICITUD_CAMBIO_TITULO: {"mimes": _PDF, "ext": {".pdf"}, "desc": "PDF"},
}

# Documentos obligatorios por modalidad (para validar al enviar).
DOCUMENTOS_REQUERIDOS = {
    ModalidadEnum.PREGRADO.value: [
        DOC_PROYECTO_PDF, DOC_PROYECTO_WORD, DOC_SOLICITUD_EVALUACION,
        DOC_CARTA_APROBACION, DOC_BOLETA_PAGO,
    ],
    ModalidadEnum.POSTGRADO.value: [
        DOC_PROYECTO_PDF, DOC_PROYECTO_WORD, DOC_SOLICITUD_EVALUACION,
        DOC_CARTA_APROBACION, DOC_BOLETA_PAGO,
    ],
    ModalidadEnum.INTERNO.value: [DOC_PROYECTO_PDF],
}

class TipoDictamenEnum(str, enum.Enum):
    """Estados permitidos para dictamen: aprobado, aprobado con observaciones o no aprobado."""
    APROBADO = "aprobado"
    APROBADO_OBSERVACIONES = "aprobado_observaciones"
    NO_APROBADO = "no_aprobado"

class Configuracion(Base):
    """Configuración global del sistema en pares clave/valor (ej. fecha límite)."""
    __tablename__ = "configuracion"

    clave = Column(String(100), primary_key=True)
    valor = Column(Text, nullable=True)
    updated_at = Column(DateTime, onupdate=func.now(), server_default=func.now())


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
    # Datos académicos del registro público (según el rol):
    #  - estudiantes (pregrado/postgrado): codigo_estudiante
    #  - investigador: laboratorio
    codigo_estudiante = Column(String(50), nullable=True)
    laboratorio = Column(String(255), nullable=True)
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
    tipo_tramite = Column(String(100), nullable=True, default="proyecto_nuevo")
    facultad = Column(String(255), nullable=True)
    # Campos del flujo dinámico de envío (Fase 1):
    modalidad = Column(String(30), nullable=True)          # pregrado / postgrado / interno
    programa_estudios = Column(String(100), nullable=True)
    ciclo = Column(String(20), nullable=True)              # pregrado (y cambio de título: incluye Egresado)
    nivel_posgrado = Column(String(50), nullable=True)     # solo postgrado
    # Solo para el trámite de cambio de título:
    numero_acta = Column(String(50), nullable=True)
    titulo_anterior = Column(Text, nullable=True)
    titulo_nuevo = Column(Text, nullable=True)
    proyecto_origen_id = Column(Integer, ForeignKey("expedientes.id"), nullable=True)  # proyecto aprobado al que aplica el cambio
    estado = Column(String(50), default="borrador")
    fecha_envio = Column(DateTime, nullable=True)
    fecha_creacion = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

    investigador = relationship("User", back_populates="expedientes")
    autores = relationship("AutorExpediente", back_populates="expediente", cascade="all, delete-orphan")
    documentos = relationship("Documento", back_populates="expediente")
    evaluaciones = relationship("Evaluacion", back_populates="expediente")
    dictamines = relationship("Dictamen", back_populates="expediente")
    notificaciones = relationship("Notificacion", back_populates="expediente")
    bitacora = relationship("Bitacora", back_populates="expediente")
    historial = relationship("HistorialExpediente", back_populates="expediente")

    @property
    def investigador_nombre(self):
        """Nombre completo del solicitante (para listados de roles internos)."""
        if self.investigador:
            return f"{self.investigador.nombre} {self.investigador.apellido}".strip()
        return None


class AutorExpediente(Base):
    """Integrantes del proyecto. El primero (orden=1) es el responsable/principal."""
    __tablename__ = "autores_expediente"

    id = Column(Integer, primary_key=True, index=True)
    expediente_id = Column(Integer, ForeignKey("expedientes.id"), nullable=False)
    orden = Column(Integer, default=1)
    apellidos_nombres = Column(String(255), nullable=False)
    codigo_estudiante = Column(String(50), nullable=True)   # no aplica a interno
    correo = Column(String(255), nullable=True)
    telefono = Column(String(50), nullable=True)
    es_principal = Column(Boolean, default=False)

    expediente = relationship("Expediente", back_populates="autores")


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
    recommendation = Column(Text)
    observaciones = Column(Text)
    completa = Column(Boolean, default=False)
    conflicto_interes = Column(Boolean, default=False)
    fecha_asignacion = Column(DateTime, server_default=func.now())
    fecha_envio = Column(DateTime, nullable=True)
    puntaje_total = Column(Integer, nullable=True)
    resultado = Column(String(50), nullable=True)

    expediente = relationship("Expediente", back_populates="evaluaciones")
    evaluador = relationship("User", back_populates="evaluaciones")
    criterios = relationship("EvaluacionCriterio", back_populates="evaluacion", cascade="all, delete-orphan")

    @property
    def titulo_protocolo(self):
        """Propiedad para acceder al título del protocolo del expediente asociado"""
        if self.expediente:
            return self.expediente.titulo_protocolo
        return None

    @property
    def investigador_nombre(self):
        """Nombre completo del solicitante del expediente asociado."""
        if self.expediente and self.expediente.investigador:
            inv = self.expediente.investigador
            return f"{inv.nombre} {inv.apellido}".strip()
        return None

    @property
    def expediente_fecha_envio(self):
        """Fecha de envío del expediente asociado (distinta de la fecha de envío de la evaluación)."""
        if self.expediente:
            return self.expediente.fecha_envio
        return None


class EvaluacionCriterio(Base):
    """Puntaje y observación de un criterio de la rúbrica para una evaluación."""
    __tablename__ = "evaluacion_criterios"

    id = Column(Integer, primary_key=True, index=True)
    evaluacion_id = Column(Integer, ForeignKey("evaluaciones.id"), nullable=False)
    criterio_key = Column(String(50), nullable=False)
    puntaje = Column(Integer, nullable=False, default=0)
    observacion = Column(Text, nullable=True)

    evaluacion = relationship("Evaluacion", back_populates="criterios")


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


CRITERIOS_RUBRICA = [
    {"key": "valor_pertinencia", "nombre": "Valor y pertinencia del estudio",
     "descripcion": "El proyecto presenta una justificación clara y una contribución académica y social relevante. Cuenta con los recursos necesarios para su implementación, incluyendo financiamiento, infraestructura, tiempo y personal capacitado.",
     "puntaje_max": 2},
    {"key": "principios_eticos", "nombre": "Principios éticos",
     "descripcion": "Respeta los principios de autonomía, beneficencia, no maleficencia y justicia.",
     "puntaje_max": 4},
    {"key": "consentimiento_informado", "nombre": "Consentimiento informado",
     "descripcion": "El proceso de información y consentimiento es adecuado, claro y voluntario. Presenta el anexo correspondiente.",
     "puntaje_max": 4},
    {"key": "proteccion_participantes", "nombre": "Protección de participantes",
     "descripcion": "Identifica riesgos y establece medidas de protección para los participantes.",
     "puntaje_max": 3},
    {"key": "poblaciones_vulnerables", "nombre": "Poblaciones vulnerables (si aplica)",
     "descripcion": "El proyecto contempla medidas especiales para proteger a poblaciones vulnerables (niños, gestantes, personas con enfermedades mentales o discapacidades, comunidades no familiarizadas con conceptos médicos, personas con libertad restringida). Si no aplica, 0 puntos.",
     "puntaje_max": 2},
    {"key": "confidencialidad_datos", "nombre": "Confidencialidad y protección de datos",
     "descripcion": "Garantiza privacidad, anonimato o confidencialidad de la información.",
     "puntaje_max": 3},
    {"key": "adecuacion_metodologica", "nombre": "Adecuación metodológica",
     "descripcion": "La metodología es robusta, clara y científicamente válida, coherente con los objetivos y no expone innecesariamente a los participantes.",
     "puntaje_max": 2},
]

PUNTAJE_TOTAL_MAX = 20

CRITERIOS_MAX_POR_KEY = {c["key"]: c["puntaje_max"] for c in CRITERIOS_RUBRICA}


def resultado_por_puntaje(total: int) -> str:
    """Deriva el resultado del dictamen según el puntaje total (0-20)."""
    if total >= 17:
        return "aprobado"
    if total >= 13:
        return "aprobado_observaciones"
    return "no_aprobado"


# Un proyecto solo puede solicitar cambio de título si ya fue aprobado
# (con o sin observaciones). Regla confirmada por el Comité.
ESTADOS_ELEGIBLE_CAMBIO_TITULO = [
    EstadoExpedienteEnum.APROBADO.value,
    EstadoExpedienteEnum.APROBADO_OBSERVACIONES.value,
]