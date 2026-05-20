# API Comité de Ética - Backend

API REST para el sistema de gestión del Comité de Ética Institucional.

---

## 📋 Tabla de Contenidos

- [Requisitos](#requisitos)
- [Instalación](#instalación)
- [Ejecución](#ejecución)
- [Mejoras Implementadas (Mayo 2026)](#mejoras-implementadas-mayo-2026)
- [Endpoints](#endpoints)
- [Autenticación](#autenticación)

---

## 🆕 Mejoras Implementadas (Mayo 2026)

### **1. Descarga y Visualización de Documentos**

**Estado:** ✅ IMPLEMENTADO

**Endpoint:**
```
GET /api/v1/expedientes/{expediente_id}/documentos/{documento_id}/descargar
```

**Descripción:**
Descarga un documento específico de un expediente. El servidor valida el acceso según el rol del usuario y registra la descarga en la bitácora.

**Headers requeridos:**
```
Authorization: Bearer <token_jwt>
```

**Response (200 OK):**
```
Content-Type: application/octet-stream
Content-Disposition: attachment; filename="protocolo.pdf"
[Contenido binario del archivo]
```

**Validación de Acceso:**
| Rol | Acceso |
|-----|--------|
| INVESTIGADOR | Solo sus propios expedientes ✅ |
| EVALUADOR | Solo expedientes asignados ✅ |
| COORDINADOR | Todos los expedientes ✅ |
| ADMINISTRADOR | Todos los expedientes ✅ |

**Errores Posibles:**
```
404 Not Found     - Expediente o documento no existe
403 Forbidden     - Usuario no tiene acceso
400 Bad Request   - Documento sin archivo asociado
```

**Ejemplo en JavaScript/React:**
```javascript
async function descargarDocumento(expedienteId, documentoId, token) {
  const response = await fetch(
    `/api/v1/expedientes/${expedienteId}/documentos/${documentoId}/descargar`,
    {
      method: 'GET',
      headers: { 'Authorization': `Bearer ${token}` }
    }
  );

  if (response.ok) {
    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = response.headers
      .get('Content-Disposition')
      .split('filename=')[1]
      .replace(/"/g, '');
    a.click();
  }
}
```

**Ejemplo en Python:**
```python
import requests

response = requests.get(
    f"http://localhost:8000/api/v1/expedientes/5/documentos/1/descargar",
    headers={"Authorization": f"Bearer {token}"}
)

if response.status_code == 200:
    with open('protocolo.pdf', 'wb') as f:
        f.write(response.content)
```

---

### **2. Titulo del Protocolo en Evaluaciones**

**Estado:** ✅ IMPLEMENTADO

**Endpoints Mejorados:**
```
GET /api/v1/evaluacion/mis-evaluaciones
GET /api/v1/evaluacion/{evaluacion_id}
PUT /api/v1/evaluacion/{evaluacion_id}
```

**Descripción:**
Todos los endpoints de evaluación ahora devuelven `titulo_protocolo` del expediente asociado, mejorando la navegación en la bandeja de evaluaciones.

**Response (GET /evaluacion/mis-evaluaciones):**
```json
[
  {
    "id": 1,
    "expediente_id": 5,
    "evaluador_id": 2,
    "titulo_protocolo": "Estudio de impacto ambiental en la región andina",
    "nivel_riesgo": "medio",
    "recommendation": "Aprobado con observaciones",
    "observaciones": "Revisar sección 3",
    "completa": false,
    "conflicto_interes": false,
    "created_at": "2026-05-19T10:30:00"
  }
]
```

**Campos Nuevos:**
- `titulo_protocolo` (string | null): Título del protocolo del expediente asignado

**Beneficios para el Frontend:**
- ✅ Muestra título sin necesidad de request adicional
- ✅ Mejor contexto en la bandeja de evaluaciones
- ✅ Navegación más intuitiva
- ✅ Optimizado con eager loading (sin N+1)

**Ejemplo en JavaScript:**
```javascript
// Obtener evaluaciones con titulo_protocolo
const response = await fetch(
  '/api/v1/evaluacion/mis-evaluaciones',
  { headers: { 'Authorization': `Bearer ${token}` } }
);

const evaluaciones = await response.json();

// Renderizar en tabla
evaluaciones.forEach(eval => {
  console.log(`${eval.titulo_protocolo} - Estado: ${eval.completa ? 'Completa' : 'Pendiente'}`);
});
```

---

### **3. Rutas de Documentos Funcionales**

**Estado:** ✅ IMPLEMENTADO

**Endpoint Existente Mejorado:**
```
GET /api/v1/expedientes/{expediente_id}/documentos
```

**Response:**
```json
[
  {
    "id": 1,
    "nombre_archivo": "protocolo.pdf",
    "tipo_documento": "protocolo",
    "ruta_archivo": "uploads/5/protocolo_abc123.pdf",
    "es_obligatorio": true,
    "validado": true,
    "version": 1,
    "created_at": "2026-05-19T10:30:00"
  }
]
```

**Flujo Completo:**

1. **Paso 1:** Obtener lista de documentos
```bash
GET /api/v1/expedientes/5/documentos
```

2. **Paso 2:** Descargar documento específico
```bash
GET /api/v1/expedientes/5/documentos/1/descargar
```

3. **Paso 3:** Archivo se descarga exitosamente ✅

---

## 📚 Endpoints

### Autenticación
- `POST /api/v1/auth/login` - Login
- `POST /api/v1/auth/logout` - Logout

### Expedientes
- `GET /api/v1/expedientes` - Listar expedientes
- `GET /api/v1/expedientes/{id}` - Obtener expediente
- `POST /api/v1/expedientes` - Crear expediente
- `PUT /api/v1/expedientes/{id}` - Actualizar expediente
- `GET /api/v1/expedientes/{id}/documentos` - Listar documentos ✨
- `GET /api/v1/expedientes/{id}/documentos/{doc_id}/descargar` - **NUEVO** ✨
- `POST /api/v1/expedientes/{id}/documentos` - Subir documento

### Evaluaciones
- `GET /api/v1/evaluacion` - Listar evaluaciones
- `GET /api/v1/evaluacion/mis-evaluaciones` - **CON titulo_protocolo** ✨
- `GET /api/v1/evaluacion/{id}` - Obtener evaluación
- `POST /api/v1/evaluacion` - Crear evaluación
- `PUT /api/v1/evaluacion/{id}` - Actualizar evaluación

### Usuarios
- `GET /api/v1/users` - Listar usuarios
- `POST /api/v1/users` - Crear usuario

---

## 🔐 Autenticación

Todos los endpoints requieren token JWT en el header:

```
Authorization: Bearer <token_jwt>
```

**Roles soportados:**
- `administrador` - Acceso total
- `coordinador` - Gestión de evaluaciones
- `evaluador` - Realizar evaluaciones
- `investigador` - Gestionar expedientes propios
- `secretaria` - Gestión administrativa

---

## ⚙️ Requisitos

- Python 3.10+
- FastAPI 0.109.0
- SQLAlchemy 2.0+
- Pydantic 2.0+

---

## 📦 Instalación

1. **Clonar el repositorio**
```bash
git clone <repo>
cd comite_backend
```

2. **Crear entorno virtual**
```bash
python -m venv env
source env/Scripts/activate  # Windows: env\Scripts\activate.bat
```

3. **Instalar dependencias**
```bash
pip install -r requirements.txt
```

---

## 🚀 Ejecución

```bash
# Modo desarrollo
uvicorn app.main:app --reload --port 8000

# Con host específico
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

**API disponible en:** `http://localhost:8000`
**OpenAPI (Swagger):** `http://localhost:8000/api/v1/openapi.json`

---

## 🧪 Pruebas

Ejecutar suite de pruebas:
```bash
python test_improvements.py
```

**Resultado esperado:** 6/6 PASADAS ✅

---

## 📝 Estructura del Proyecto

```
comite_backend/
├── app/
│   ├── api/
│   │   ├── auth/
│   │   ├── expedientes/
│   │   ├── evaluacion/
│   │   ├── users/
│   │   └── ...
│   ├── models/
│   ├── schemas/
│   ├── core/
│   ├── db/
│   └── main.py
├── uploads/          ← Documentos guardados aquí
├── requirements.txt
├── README.md
└── test_improvements.py
```

---

## 📂 Almacenamiento de Documentos

Los documentos se guardan en:
```
uploads/{expediente_id}/{nombre_archivo}
```

**Ejemplo:**
```
uploads/5/protocolo_abc123.pdf
uploads/5/presupuesto_def456.xlsx
```

---

## 🔍 Validación de Documentos

**Tipos permitidos:**
- PDF (application/pdf)
- Word (application/msword, .docx)
- Excel (application/vnd.ms-excel, .xlsx)
- Texto (.txt)

**Extensiones:** `.pdf`, `.doc`, `.docx`, `.xls`, `.xlsx`, `.txt`

**Tamaño máximo:** 10 MB

---

## 📊 Cambios Recientes (19/05/2026)

| # | Tarea | Estado |
|---|-------|--------|
| 1 | Endpoint descarga documentos | ✅ COMPLETO |
| 2 | `titulo_protocolo` en evaluaciones | ✅ COMPLETO |
| 3 | Validación y pruebas | ✅ COMPLETO |

**Archivos modificados:**
- `app/api/expedientes/routes.py`
- `app/api/evaluacion/routes.py`
- `app/models/__init__.py`
- `app/schemas/__init__.py`

---

## 🎯 Próximas Tareas

- [ ] Implementar API de IA (pendiente Johana)
- [ ] Endpoint preview de documentos (opcional)
- [ ] Logs detallados de descargas
- [ ] Compresión de archivos

---

## 📞 Contacto

**Encargado Backend:** Erasmo

**Fecha de actualización:** 19 de Mayo de 2026

---

## ✨ Estado General

```
✅ Descarga de documentos
✅ Titulo protocolo en evaluaciones
✅ Rutas funcionales
✅ Control de acceso
✅ Bitácora de auditoría
⏳ API de IA (pendiente)
```

