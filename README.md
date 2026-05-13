# Comité de Ética - Backend API

API REST para el sistema de gestión de evaluaciones del Comité de Ética.

## 📋 Tabla de contenidos

- [Instalación](#instalación)
- [Configuración](#configuración)
- [Ejecutar el servidor](#ejecutar-el-servidor)
- [Documentación de APIs](#documentación-de-apis)
- [Testing](#testing)
- [Endpoints mejorados](#endpoints-mejorados)

---

## ⚙️ Instalación

### Requisitos
- Python 3.10+
- pip

### Pasos

1. **Clonar el repositorio**
```bash
git clone <tu-repo>
cd comite_backend
```

2. **Crear entorno virtual**
```bash
python -m venv env
```

3. **Activar entorno virtual**

**En Windows:**
```bash
env\Scripts\activate
```

**En Mac/Linux:**
```bash
source env/bin/activate
```

4. **Instalar dependencias**
```bash
pip install -r requirements.txt
```

---

## 🔧 Configuración

### Variables de entorno (`.env`)

Crea un archivo `.env` en la raíz del proyecto:

```env
# Base de datos (PostgreSQL Render)
DATABASE_URL=postgresql://admin:PASSWORD@dpg-xxxxxx.oregon-postgres.render.com/comite?sslmode=require

# Seguridad
SECRET_KEY=your-secret-key-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60

# Hosts permitidos
ALLOWED_HOSTS=["*"]
```

> **Nota:** Obtén tu `DATABASE_URL` desde tu instancia PostgreSQL en Render.

---

## 🚀 Ejecutar el servidor

```bash
python -m uvicorn app.main:app --reload
```

El servidor estará disponible en: **`http://localhost:8000`**

### Documentación interactiva

- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc
- **OpenAPI JSON:** http://localhost:8000/api/v1/openapi.json

---

## 📚 Documentación de APIs

### 1. Autenticación

#### POST /api/v1/auth/register

Crear un nuevo usuario.

**Request:**
```json
{
  "email": "usuario@comite.edu",
  "password": "Password123",
  "nombre": "Juan",
  "apellido": "Pérez",
  "rol": "investigador",
  "especialidad": "Biología"
}
```

**Response:**
```json
{
  "id": 1,
  "email": "usuario@comite.edu",
  "nombre": "Juan",
  "apellido": "Pérez",
  "rol": "investigador",
  "activo": true,
  "especialidad": "Biología",
  "created_at": "2026-05-12T15:30:00"
}
```

#### POST /api/v1/auth/login

Autenticar usuario y obtener token JWT.

**Request (form-data):**
```
username: usuario@comite.edu
password: Password123
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

---

## 🎯 Endpoints Mejorados

### Observaciones del Frontend

El equipo de frontend indicó que necesitaban:
1. ✅ Más metadatos al crear expedientes (tipo_tramite, facultad, prioridad)
2. ✅ Upload de archivos binarios (no query params)
3. ✅ Endpoint para asignar evaluadores manualmente (no solo automático)
4. ✅ Datos persistentes (no borrase cada reinicio)

**Todos estos puntos fueron implementados y probados.** ✅

---

### 1. POST /api/v1/expedientes/ (MEJORADO ⭐)

Crear un nuevo expediente con metadatos completos.

**Observación resuelta:** Ahora acepta `tipo_tramite`, `facultad` y `prioridad` (antes solo `titulo_protocolo`).

**Request:**
```bash
curl -X POST "http://localhost:8000/api/v1/expedientes/" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "titulo_protocolo": "Estudio de efectividad de vacunas COVID-19",
    "tipo_tramite": "investigacion_biomedica",
    "facultad": "Medicina",
    "prioridad": "alta"
  }'
```

**Response (201 Created):**
```json
{
  "id": 1,
  "codigo_unico": "CE-A1B2C3D4",
  "titulo_protocolo": "Estudio de efectividad de vacunas COVID-19",
  "investigador_id": 1,
  "tipo_tramite": "investigacion_biomedica",
  "facultad": "Medicina",
  "prioridad": "alta",
  "estado": "borrador",
  "fecha_envio": null,
  "created_at": "2026-05-12T15:30:00"
}
```

**Campos:**
- `titulo_protocolo` (string, requerido): Título del protocolo/investigación
- `tipo_tramite` (string, opcional): Tipo de trámite (ej: investigacion_biomedica, investigacion_experimental)
- `facultad` (string, opcional): Facultad responsable
- `prioridad` (string, opcional): Nivel de prioridad (baja, normal, alta, urgente)

---

### 2. PUT /api/v1/expedientes/{expediente_id} (MEJORADO ⭐)

Actualizar expediente con nuevos campos de metadatos.

**Observación resuelta:** Ahora puedes actualizar `tipo_tramite`, `facultad` y `prioridad`.

**Request:**
```bash
curl -X PUT "http://localhost:8000/api/v1/expedientes/1" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "tipo_tramite": "investigacion_experimental",
    "facultad": "Ingenieria",
    "prioridad": "media",
    "estado": "en_revision"
  }'
```

**Response (200 OK):**
```json
{
  "id": 1,
  "codigo_unico": "CE-A1B2C3D4",
  "titulo_protocolo": "Estudio de efectividad de vacunas COVID-19",
  "investigador_id": 1,
  "tipo_tramite": "investigacion_experimental",
  "facultad": "Ingenieria",
  "prioridad": "media",
  "estado": "en_revision",
  "fecha_envio": null,
  "created_at": "2026-05-12T15:30:00"
}
```

**Campos opcionales:**
- `titulo_protocolo`
- `tipo_tramite`
- `facultad`
- `prioridad`
- `estado`

---

### 3. POST /api/v1/expedientes/{expediente_id}/documentos (CORREGIDO ⭐⭐)

Subir documento binario al expediente (ahora con file upload real).

**Observación resuelta:** Cambié de query params a multipart/form-data con archivo binario.

**Request (form-data):**
```bash
curl -X POST "http://localhost:8000/api/v1/expedientes/1/documentos" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@/ruta/al/protocolo.pdf" \
  -F "tipo_documento=protocolo" \
  -F "es_obligatorio=true"
```

**Response (201 Created):**
```json
{
  "id": 1,
  "nombre_archivo": "protocolo.pdf",
  "tipo_documento": "protocolo",
  "es_obligatorio": true,
  "validado": false,
  "version": 1,
  "ruta_archivo": "uploads/1/protocolo.pdf",
  "created_at": "2026-05-12T15:30:00"
}
```

**Campos:**
- `file` (file, requerido): Archivo binario a subir (PDF, DOCX, etc.)
- `tipo_documento` (string, opcional): Tipo de documento (ej: protocolo, consentimiento, presupuesto)
- `es_obligatorio` (boolean, opcional): ¿Es documento obligatorio? (default: true)

**Almacenamiento:**
Los archivos se guardan en: `uploads/{expediente_id}/{nombre_archivo}`

---

### 4. POST /api/v1/evaluacion/expediente/{expediente_id}/asignar (NUEVO ⭐⭐)

Permitir al coordinador asignar evaluadores manualmente (no solo automático).

**Observación resuelta:** Antes solo el backend asignaba automáticamente. Ahora el coordinador puede seleccionar.

**Request:**
```bash
curl -X POST "http://localhost:8000/api/v1/evaluacion/expediente/1/asignar" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "evaluador_id": 2
  }'
```

**Response (201 Created):**
```json
{
  "message": "Evaluador asignado exitosamente",
  "evaluacion_id": 5,
  "evaluador": {
    "id": 2,
    "nombre": "Juan",
    "apellido": "Evaluador"
  },
  "expediente_codigo": "CE-A1B2C3D4"
}
```

**Validaciones:**
- ✅ Solo coordinadores/administradores pueden usar este endpoint
- ✅ Máximo 2 evaluadores por expediente
- ✅ El evaluador debe tener rol de evaluador
- ✅ El evaluador debe estar activo
- ✅ No se puede asignar dos veces el mismo evaluador
- ✅ Se notifica automáticamente al evaluador

**Campos:**
- `evaluador_id` (integer, requerido): ID del usuario evaluador a asignar

**Notificación automática:**
Se crea automáticamente una notificación para el evaluador:
```json
{
  "usuario_id": 2,
  "expediente_id": 1,
  "titulo": "Nueva evaluación asignada",
  "mensaje": "Se te ha asignado la evaluación del expediente: CE-A1B2C3D4 - Estudio de efectividad de vacunas COVID-19"
}
```

---

## 🧪 Testing

### Ejecutar script de prueba completo

Se incluye un script `test_endpoints.py` que prueba todos los 4 endpoints:

```bash
python test_endpoints.py
```

Este script:
1. ✅ Crea usuario (o usa existente)
2. ✅ Obtiene token JWT
3. ✅ Crea expediente con metadatos
4. ✅ Actualiza expediente
5. ✅ Sube documento real
6. ✅ Asigna evaluador manualmente
7. ✅ Muestra resultados detallados

**Output esperado:**
```
============================================================
  PASO 1: Autenticación
============================================================
✅ Login exitoso

============================================================
  PASO 2: POST /api/v1/expedientes/ (MEJORADO)
============================================================
✅ Expediente creado exitosamente

============================================================
  PASO 3: PUT /api/v1/expedientes/{id} (MEJORADO)
============================================================
✅ Expediente actualizado exitosamente

============================================================
  PASO 4: POST /api/v1/expedientes/{id}/documentos (CORREGIDO)
============================================================
✅ Documento subido exitosamente

============================================================
  PASO 5: POST /api/v1/evaluacion/expediente/{id}/asignar (NUEVO)
============================================================
✅ Evaluador asignado exitosamente
```

### Probar en Swagger UI

1. Ve a: http://localhost:8000/docs
2. Click en "Authorize" (botón arriba a la derecha)
3. Ingresa tu token JWT
4. Prueba los endpoints interactivamente

---

## 📊 Estructura de base de datos

### Tablas principales

```
users
├── id (PK)
├── email (UNIQUE)
├── password_hash
├── nombre
├── apellido
├── rol (administrador, coordinador, evaluador, investigador, etc.)
├── especialidad
├── carga_trabajo
├── conflicto_interes
└── created_at

expedientes
├── id (PK)
├── codigo_unico (UNIQUE)
├── titulo_protocolo
├── investigador_id (FK -> users.id)
├── tipo_tramite
├── facultad
├── prioridad
├── estado (borrador, enviado, en_revision, subsanacion, aprobado, rechazado, archivado)
├── fecha_envio
└── created_at

documentos
├── id (PK)
├── expediente_id (FK -> expedientes.id)
├── nombre_archivo
├── tipo_documento
├── ruta_archivo
├── version
├── es_obligatorio
├── validado
└── created_at

evaluaciones
├── id (PK)
├── expediente_id (FK -> expedientes.id)
├── evaluador_id (FK -> users.id)
├── nivel_riesgo
├── recommendation
├── observaciones
├── completa
├── conflicto_interes
├── fecha_asignacion
└── fecha_envio
```

---

## 🔐 Roles y permisos

| Rol | Crear Expediente | Subir Documentos | Ver Expedientes | Asignar Evaluadores |
|-----|-----------------|-----------------|-----------------|-------------------|
| Investigador | ✅ Propios | ✅ Propios | ✅ Propios | ❌ |
| Evaluador | ❌ | ❌ | ✅ Sus evaluaciones | ❌ |
| Coordinador | ✅ Todos | ✅ Todos | ✅ Todos | ✅ |
| Secretaria | ✅ Todos | ✅ Todos | ✅ Todos | ❌ |
| Administrador | ✅ Todos | ✅ Todos | ✅ Todos | ✅ |

---

## 🌍 Despliegue en Render

### 1. Crear servicio web en Render

```bash
git push heroku main
```

### 2. Variables de entorno en Render

En la configuración del servicio, añade:
- `DATABASE_URL`: Tu URL de PostgreSQL en Render
- `SECRET_KEY`: Una clave secreta fuerte
- `ALLOWED_HOSTS`: Dominio de tu app

### 3. La BD persiste automáticamente

Los datos NO se pierden nunca porque PostgreSQL en Render es un servicio persistente.

---

## 📝 Cambios recientes

### Versión 1.1 (Resolución de observaciones del frontend)

**Cambios:**
1. ✅ **POST /expedientes/** - Ampliado con campos: `tipo_tramite`, `facultad`, `prioridad`
2. ✅ **PUT /expedientes/{id}** - Ahora actualiza nuevos campos de metadatos
3. ✅ **POST /expedientes/{id}/documentos** - Convertido a file upload binario (multipart/form-data)
4. ✅ **POST /evaluacion/expediente/{id}/asignar** - Nuevo endpoint para asignación manual
5. ✅ **Base de datos** - Migrada a PostgreSQL Render para persistencia

**Probado:** Todos los endpoints funciona 100% ✅

---

## 🛠️ Troubleshooting

### Error: `401 Unauthorized`
- Verifica que estés enviando el token JWT en el header: `Authorization: Bearer YOUR_TOKEN`
- El token puede haber expirado (default: 60 minutos)

### Error: `422 Unprocessable Entity`
- Revisa que estés enviando los campos correctos en el JSON
- Verifica los tipos de datos (string, integer, boolean, etc.)

### Error: `404 Not Found`
- El expediente/usuario no existe
- Verifica el ID que estás usando

### Error: `403 Forbidden`
- No tienes permisos para esta acción
- Verifica tu rol y el endpoint

---

## 📞 Soporte

Para reportar bugs o hacer sugerencias, contacta al equipo de desarrollo.

---

**Última actualización:** 12 de mayo de 2026

