# API Comité de Ética - Backend

Backend FastAPI para el sistema de gestión de protocolos del Comité de Ética.

## Inicio Rápido

### Requisitos
- Python 3.10+
- pip

### Instalación

#### Opción 1: Docker (Recomendado)
```bash
# Construir imagen
docker build -t comite-backend .

# Ejecutar
docker run -p 8000:8000 --env-file .env comite-backend
```

#### Opción 2: Local sin Docker
```bash
# Crear entorno virtual (opcional)
python -m venv env
source env/bin/activate  # Linux/Mac
# En Windows: env\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt
```

### Configuración

Crear archivo `.env`:
```env
DATABASE_URL=sqlite:///./comite.db
SECRET_KEY=tu-secret-key-aqui
```

### Ejecutar

```bash
uvicorn app.main:app --reload
```

El servidor estará en: `http://localhost:8000`
Documentación Swagger: `http://localhost:8000/docs`

---

## URL Base (Producción)

```
https://comite-backend.onrender.com/api/v1
```

**Documentación Swagger (OpenAPI)**: https://comite-backend.onrender.com/docs

> **Nota para Frontend**: El frontend debe conectar a `https://comite-backend.onrender.com/api/v1`

> **Nota para Frontend**: Reemplazar `http://localhost:8000/api/v1` por la URL de producción cuando el backend esté desplegado en Render.

---

## Autenticación

### Login (JSON)

**Endpoint**: `POST /auth/login-json`

**Request**:
```json
{
  "correo": "usuario@demo.edu",
  "rol": "investigador",
  "password": "password123"
}
```

**Response** (200):
```json
{
  "usuario": {
    "id": 1,
    "email": "usuario@demo.edu",
    "nombre": "Ana",
    "apellido": "Lopez",
    "rol": "investigador",
    "activo": true,
    "especialidad": null,
    "carga_trabajo": null,
    "conflicto_interes": false,
    "created_at": "2026-05-04T05:35:40"
  },
  "redirectTo": "/investigador/dashboard"
}
```

**Redirects por rol**:
| Rol | Redirect |
|-----|----------|
| investigador | `/investigador/dashboard` |
| secretaria | `/secretaria/bandeja` |
| coordinador | `/coordinador/dashboard` |
| evaluador | `/evaluador/bandeja` |
| administrador | `/admin/configuracion` |

**Errores**:
- 401: Credenciales incorrectas o rol no válido

---

### Registro de Usuario

**Endpoint**: `POST /auth/register`

**Request** (formato frontend):
```json
{
  "nombres": "Ana",
  "apellidos": "Lopez",
  "correo": "ana@demo.edu",
  "rol": "investigador",
  "password": "password123"
}
```

**Request** (formato alternativo):
```json
{
  "nombre": "Ana",
  "apellido": "Lopez",
  "email": "ana@demo.edu",
  "rol": "investigador",
  "password": "password123"
}
```

**Request** (evaluador con campos extras):
```json
{
  "nombres": "Jorge",
  "apellidos": "Perez",
  "correo": "jorge@demo.edu",
  "rol": "evaluador",
  "password": "password123",
  "especialidad": "Bioetica",
  "carga_trabajo": 4,
  "conflicto_interes": false
}
```

**Response** (200):
```json
{
  "id": 1,
  "email": "ana@demo.edu",
  "nombre": "Ana",
  "apellido": "Lopez",
  "rol": "investigador",
  "activo": true,
  "especialidad": null,
  "carga_trabajo": null,
  "conflicto_interes": false,
  "created_at": "2026-05-04T05:35:40"
}
```

---

## Módulo: Users

### GET /users/me

Obtiene la información del usuario autenticado.

**Headers**: `Authorization: Bearer <token>`

**Response** (200):
```json
{
  "id": 1,
  "email": "usuario@demo.edu",
  "nombre": "Ana",
  "apellido": "Lopez",
  "rol": "investigador",
  "activo": true,
  "especialidad": null,
  "carga_trabajo": null,
  "conflicto_interes": false,
  "created_at": "2026-05-04T05:35:40"
}
```

---

### GET /users/

Lista todos los usuarios (solo admin/coordinador/secretaria).

**Headers**: `Authorization: Bearer <token>`

**Query Params**:
- `skip`: número de registros a omitir (default: 0)
- `limit`: límite de resultados (default: 100)

**Response** (200):
```json
[
  {
    "id": 1,
    "email": "usuario@demo.edu",
    "nombre": "Ana",
    "apellido": "Lopez",
    "rol": "investigador",
    "activo": true,
    "created_at": "2026-05-04T05:35:40"
  }
]
```

---

### GET /users/{id}

Obtiene un usuario específico.

**Headers**: `Authorization: Bearer <token>`

**Response** (200): Ver formato de /users/me

**Errores**:
- 404: Usuario no encontrado

---

### PUT /users/{id}

Actualiza un usuario.

**Headers**: `Authorization: Bearer <token>`

**Request**:
```json
{
  "nombre": "Nuevo Nombre",
  "apellido": "Nuevo Apellido",
  "rol": "coordinador",
  "activo": true
}
```

**Nota**: Solo administradores pueden modificar `rol` y `activo`.

**Response** (200): Usuario actualizado

**Errores**:
- 403: No tienes permisos
- 404: Usuario no encontrado

---

### DELETE /users/{id}

Desactiva un usuario (soft delete).

**Headers**: `Authorization: Bearer <token>`

**Response** (200):
```json
{
  "message": "Usuario desactivado"
}
```

**Errores**:
- 403: Solo administradores pueden eliminar usuarios

---

## Módulo: Expedientes

### GET /expedientes/

Lista expedients según el rol del usuario.

**Headers**: `Authorization: Bearer <token>`

**Query Params**:
- `skip`: número de registros a omitir (default: 0)
- `limit`: límite de resultados (default: 50)

**Response** (200):
```json
[
  {
    "id": 1,
    "titulo_protocolo": "Estudio de...",
    "codigo_unico": "CE-ABC12345",
    "investigador_id": 1,
    "estado": "borrador",
    "fecha_envio": null,
    "created_at": "2026-05-04T05:35:40"
  }
]
```

---

### POST /expedientes/

Crea un nuevo expediente.

**Headers**: `Authorization: Bearer <token>`

**Request**:
```json
{
  "titulo_protocolo": "Nuevo estudio de investigación"
}
```

**Response** (200):
```json
{
  "id": 1,
  "titulo_protocolo": "Nuevo estudio de investigación",
  "codigo_unico": "CE-ABC12345",
  "investigador_id": 1,
  "estado": "borrador",
  "fecha_envio": null,
  "created_at": "2026-05-04T05:35:40"
}
```

---

### GET /expedientes/{id}

Obtiene un expediente específico.

**Headers**: `Authorization: Bearer <token>`

**Response** (200): Ver formato de GET /expedientes/

**Errores**:
- 404: Expediente no encontrado
- 403: No tienes acceso a este expediente

---

### PUT /expedientes/{id}

Actualiza un expediente.

**Headers**: `Authorization: Bearer <token>`

**Request**:
```json
{
  "titulo_protocolo": "Título actualizado",
  "estado": "aprobado"
}
```

**Response** (200): Expediente actualizado

**Errores**:
- 404: Expediente no encontrado
- 403: No puedes modificar un expediente enviado

---

### POST /expedientes/{id}/enviar

Envía formalmente un expediente.

**Headers**: `Authorization: Bearer <token>`

**Response** (200):
```json
{
  "message": "Expediente enviado exitosamente",
  "codigo": "CE-ABC12345"
}
```

**Errores**:
- 404: Expediente no encontrado
- 400: El expediente ya fue enviado

---

### GET /expedientes/{id}/bitacora

Obtiene la bitácora de un expediente.

**Headers**: `Authorization: Bearer <token>`

**Response** (200):
```json
[
  {
    "id": 1,
    "accion": "Expediente creado",
    "detalle": "Título: Estudio de...",
    "created_at": "2026-05-04T05:35:40"
  }
]
```

---

### GET /expedientes/{id}/historial

Obtiene el historial de estados de un expediente.

**Headers**: `Authorization: Bearer <token>`

**Response** (200):
```json
[
  {
    "id": 1,
    "expediente_id": 1,
    "estado_anterior": "borrador",
    "estado_nuevo": "enviado",
    "observaciones": null,
    "created_at": "2026-05-04T05:35:40"
  }
]
```

---

### POST /expedientes/{id}/documentos

Agrega un documento a un expediente.

**Headers**: `Authorization: Bearer <token>`

**Request** (form-data):
- `nombre_archivo`: string
- `tipo_documento`: string
- `es_obligatorio`: boolean (default: true)

**Response** (200):
```json
{
  "id": 1,
  "expediente_id": 1,
  "nombre_archivo": "protocolo.pdf",
  "tipo_documento": "PDF",
  "es_obligatorio": true,
  "validado": false,
  "version": 1,
  "created_at": "2026-05-04T05:35:40"
}
```

**Errores**:
- 404: Expediente no encontrado
- 400: No puedes agregar documentos en este estado

---

## Módulo: Evaluación

### GET /evaluacion/

Lista evaluaciones según el rol.

**Headers**: `Authorization: Bearer <token>`

**Query Params**:
- `skip`: número de registros a omitir
- `limit`: límite de resultados

**Response** (200):
```json
[
  {
    "id": 1,
    "expediente_id": 1,
    "evaluador_id": 2,
    "nivel_riesgo": "medio",
    "recommendation": "aprobar",
    "observaciones": "Observaciones...",
    "completa": false,
    "conflicto_interes": false,
    "created_at": "2026-05-04T05:35:40"
  }
]
```

---

### POST /evaluacion/

Crea una nueva evaluación (solo coordinadores).

**Headers**: `Authorization: Bearer <token>`

**Request**:
```json
{
  "expediente_id": 1
}
```

**Response** (200):
```json
{
  "id": 1,
  "expediente_id": 1,
  "evaluador_id": 2,
  "nivel_riesgo": null,
  "recommendation": null,
  "observaciones": null,
  "completa": false,
  "conflicto_interes": false,
  "created_at": "2026-05-04T05:35:40"
}
```

**Errores**:
- 403: Solo coordinadores pueden crear evaluaciones
- 404: Expediente no encontrado
- 400: Ya hay 2 evaluadores asignados

---

### GET /evaluacion/{id}

Obtiene una evaluación específica.

**Headers**: `Authorization: Bearer <token>`

**Response** (200): Ver formato de GET /evaluacion/

**Errores**:
- 404: Evaluación no encontrada

---

### PUT /evaluacion/{id}

Actualiza una evaluación.

**Headers**: `Authorization: Bearer <token>`

**Request**:
```json
{
  "nivel_riesgo": "alto",
  "recommendation": "desaprobar",
  "observaciones": "El protocolo tiene fallas éticas",
  "completa": true
}
```

**Response** (200): Evaluación actualizada

**Errores**:
- 404: Evaluación no encontrada
- 403: No puedes modificar esta evaluación

---

### POST /evaluacion/{id}/conflicto

Declara conflicto de interés en una evaluación.

**Headers**: `Authorization: Bearer <token>`

**Response** (200):
```json
{
  "message": "Conflicto de interés declarado"
}
```

**Errores**:
- 404: Evaluación no encontrada
- 403: No puedes declarar conflicto por otro evaluador

---

### POST /evaluacion/{id}/guardar-parcial

Guarda parcialmente una evaluación.

**Headers**: `Authorization: Bearer <token>`

**Request**:
```json
{
  "nivel_riesgo": "medio",
  "observaciones": "Evaluación en progreso..."
}
```

**Response** (200):
```json
{
  "message": "Guardado parcial exitoso"
}
```

**Errores**:
- 404: Evaluación no encontrada
- 403: No tienes acceso

---

## Módulo: Dictamen

### GET /dictamen/

Lista todos los dictámenes.

**Headers**: `Authorization: Bearer <token>`

**Query Params**:
- `skip`: número de registros a omitir
- `limit`: límite de resultados

**Response** (200):
```json
[
  {
    "id": 1,
    "expediente_id": 1,
    "numero_dictamen": "DICT-2026-A1B2C3",
    "tipo_dictamen": "aprobado",
    "contenido": "El comité resuelve aprobar...",
    "firmado": false,
    "created_at": "2026-05-04T05:35:40"
  }
]
```

---

### POST /dictamen/

Crea un nuevo dictamen (solo coordinadores).

**Headers**: `Authorization: Bearer <token>`

**Request**:
```json
{
  "expediente_id": 1,
  "contenido": "El comité resuelve aprobar el protocolo..."
}
```

**Query Params**:
- `tipo_dictamen`: string (default: "aprobado")

**Response** (200): Dictamen creado

**Errores**:
- 403: Solo coordinadores pueden generar dictámenes
- 404: Expediente no encontrado
- 400: Se necesitan al menos 2 evaluaciones completas para generar dictamen

---

### GET /dictamen/{id}

Obtiene un dictamen específico.

**Headers**: `Authorization: Bearer <token>`

**Response** (200): Ver formato de GET /dictamen/

**Errores**:
- 404: Dictamen no encontrado

---

### PUT /dictamen/{id}

Actualiza un dictamen.

**Headers**: `Authorization: Bearer <token>`

**Request**:
```json
{
  "contenido": "Contenido actualizado",
  "firmado": true
}
```

**Response** (200): Dictamen actualizado

**Errores**:
- 404: Dictamen no encontrado
- 403: No tienes permisos

---

### POST /dictamen/{id}/firma

Firma un dictamen (solo coordinadores).

**Headers**: `Authorization: Bearer <token>`

**Response** (200):
```json
{
  "message": "Dictamen firmado exitosamente",
  "numero": "DICT-2026-A1B2C3"
}
```

**Errores**:
- 403: Solo coordinadores pueden firmar
- 404: Dictamen no encontrado
- 400: El dictamen no tiene contenido

---

## Módulo: Notificaciones

### GET /notificaciones/

Lista las notificaciones del usuario actual.

**Headers**: `Authorization: Bearer <token>`

**Query Params**:
- `skip`: número de registros a omitir
- `limit`: límite de resultados

**Response** (200):
```json
[
  {
    "id": 1,
    "usuario_id": 1,
    "expediente_id": 1,
    "titulo": "Nuevo mensaje",
    "mensaje": "Su expediente ha sido revisado",
    "leida": false,
    "created_at": "2026-05-04T05:35:40"
  }
]
```

---

### GET /notificaciones/sin-leer

Cuenta las notificaciones no leídas.

**Headers**: `Authorization: Bearer <token>`

**Response** (200):
```json
{
  "sin_leer": 5
}
```

---

### GET /notificaciones/{id}

Obtiene una notificación específica.

**Headers**: `Authorization: Bearer <token>`

**Response** (200): Ver formato de GET /notificaciones/

**Errores**:
- 404: Notificación no encontrada

---

### PUT /notificaciones/{id}

Marca una notificación como leída/no leída.

**Headers**: `Authorization: Bearer <token>`

**Request**:
```json
{
  "leida": true
}
```

**Response** (200): Notificación actualizada

**Errores**:
- 404: Notificación no encontrada

---

## Módulo: Reportes

### GET /reportes/expedientes-por-estado

Reporta expedients agrupados por estado.

**Headers**: `Authorization: Bearer <token>`

**Response** (200):
```json
[
  {
    "estado": "borrador",
    "total": 10
  },
  {
    "estado": "enviado",
    "total": 5
  }
]
```

---

### GET /reportes/tiempos-atencion

Reporta tiempos de atención de expedients.

**Headers**: `Authorization: Bearer <token>`

**Response** (200):
```json
[
  {
    "expediente_id": 1,
    "codigo": "CE-ABC12345",
    "dias": 5,
    "estado": "enviado"
  }
]
```

---

### GET /reportes/carga-evaluadores

Reporta la carga de trabajo de evaluadores.

**Headers**: `Authorization: Bearer <token>`

**Response** (200):
```json
[
  {
    "evaluador_id": 2,
    "total": 8
  }
]
```

---

### GET /reportes/resultados-emitidos

Reporta los dictámenes emitidos agrupados por tipo.

**Headers**: `Authorization: Bearer <token>`

**Response** (200):
```json
[
  {
    "tipo": "aprobado",
    "total": 15
  },
  {
    "tipo": "desaprobado",
    "total": 3
  }
]
```

---

### GET /reportes/buscar-expedientes

Busca expedients por filtros.

**Headers**: `Authorization: Bearer <token>`

**Query Params**:
- `estado`: filtrar por estado
- `fecha_inicio`: fecha inicio (formato ISO)
- `fecha_fin`: fecha fin (formato ISO)

**Response** (200): Lista de expedients

---

## Roles Disponibles

- `investigador`
- `secretaria`
- `coordinador`
- `evaluador`
- `administrador`

---

## Estados de Expediente

- `borrador`
- `enviado`
- `en_revision`
- `subsanacion`
- `aprobado`
- `rechazado`
- `archivado`

---

## Recomendaciones de Evaluación

- `aprobar`
- `aprobar_con_observaciones`
- `solicitar_subsanacion`
- `desaprobar`

---

## Notas para Frontend

1. Todos los endpoints (excepto auth) requieren el header `Authorization: Bearer <token>`
2. El token se obtiene del endpoint `/auth/login`
3. Los campos aceptados para registro son: `nombres`, `apellidos`, `correo`, `rol`, `password`
4. Para evaluadores, opcionalmente incluir: `especialidad`, `carga_trabajo`, `conflicto_interes`
5. Las fechas en requests deben usar formato ISO (YYYY-MM-DD)