# Comité de Ética - Backend API

API REST para la gestión de expedientes, evaluaciones y dictámenes del Comité de Ética.

---

## 🚀 Mejoras Implementadas (Mayo 2026)

### 1️⃣ Headers Mejorados en Descarga de Documentos

El endpoint `/descargar` ahora retorna headers optimizados:

- **Content-Type Automático**: Detecta el tipo MIME del archivo (PDF, DOCX, XLSX, TXT, etc.)
- **Content-Disposition con UTF-8**: Soporta nombres de archivo con caracteres especiales
- **CORS Headers Expuestos**: Permite acceso desde el frontend a `Content-Disposition`, `Content-Type`, `Content-Length`

**Para el Frontend:**
```javascript
// Descargar documento
const response = await fetch(
  `${API_URL}/expedientes/${expedienteId}/documentos/${documentoId}/descargar`,
  {
    method: 'GET',
    headers: {
      'Authorization': `Bearer ${token}`
    }
  }
);

// El archivo se descargará automáticamente con el nombre original
const blob = await response.blob();
const url = window.URL.createObjectURL(blob);
const a = document.createElement('a');
a.href = url;
a.download = response.headers.get('content-disposition')?.split('filename=')[1] || 'documento';
a.click();
```

---

### 2️⃣ Documentación OpenAPI como Respuesta Binaria

El Swagger UI (`/docs`) ahora documenta correctamente las respuestas de descarga:

- ✅ Response 200 se documenta como **`application/octet-stream` (binario)**
- ✅ Headers incluidos: `Content-Disposition`, `Content-Type`, `Content-Length`
- ✅ Swagger UI muestra correctamente que retorna un archivo, no JSON

**Para el Frontend:**
- Consulta el `/docs` del backend para ver la documentación actualizada
- Los tipos de respuesta están correctamente especificados
- No hay sorpresas: sabes exactamente qué esperar de la API

---

### 3️⃣ Nuevo Endpoint: `/preview` para Previsualización

Nuevo endpoint dedicado para previsualizar documentos en el navegador (diferente de descargar).

#### Endpoint de Descarga (ya existente, mejorado)
```
GET /expedientes/{expediente_id}/documentos/{documento_id}/descargar
```
- **Content-Disposition**: `attachment` → Descarga el archivo
- **Uso**: Cuando el usuario presiona "Descargar"
- **Resultado**: Archivo se guarda en carpeta Downloads

#### Nuevo Endpoint de Previsualización
```
GET /expedientes/{expediente_id}/documentos/{documento_id}/preview
```
- **Content-Disposition**: `inline` → Abre el archivo en navegador
- **Uso**: Cuando el usuario presiona "Ver" o "Abrir"
- **Resultado**: PDF/documento se abre en una pestaña nueva (si el navegador lo soporta)

**Para el Frontend - Botón "Ver":**
```javascript
// Previsualizar documento en navegador
const previewDocument = (expedienteId, documentoId) => {
  const previewUrl = `${API_URL}/expedientes/${expedienteId}/documentos/${documentoId}/preview?token=${token}`;
  window.open(previewUrl, '_blank');
};
```

**Para el Frontend - Botón "Descargar":**
```javascript
// Descargar documento
const downloadDocument = async (expedienteId, documentoId, fileName) => {
  const response = await fetch(
    `${API_URL}/expedientes/${expedienteId}/documentos/${documentoId}/descargar`,
    {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${token}`
      }
    }
  );
  
  const blob = await response.blob();
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = fileName;
  a.click();
  window.URL.revokeObjectURL(url);
};
```

---

## 📋 Resumen de Cambios

| Feature | Antes | Ahora |
|---------|-------|-------|
| Content-Type | Siempre `application/octet-stream` | Detectado automáticamente |
| Nombres UTF-8 | No soportaba caracteres especiales | ✅ Soporta ñ, é, etc. |
| CORS Headers | No expuestos | ✅ Accesibles desde frontend |
| Preview vs Download | Solo descarga | ✅ 2 endpoints distintos |
| OpenAPI | Mostrado como JSON | ✅ Documentado como binario |
| Bitácora | Se registraba descarga | ✅ Se registra descarga y preview |

---

## 🔐 Control de Acceso

Ambos endpoints (`/descargar` y `/preview`) respetan el control de acceso:

- **Investigador**: Solo sus propios expedientes
- **Evaluador**: Solo expedientes asignados para evaluación
- **Admin/Coordinador/Secretaria**: Todos los expedientes

**Respuestas posibles:**
- `200 OK`: Archivo descargado/previsualizador
- `403 Forbidden`: Sin acceso al expediente
- `404 Not Found`: Expediente o documento no existe
- `400 Bad Request`: Documento sin ruta válida

---

## 🧪 Validación

Todas las mejoras han sido validadas con pruebas unitarias (10/10 pasadas):

```bash
pytest test_improvements.py -v
```

✅ Endpoints registrados correctamente
✅ Headers Content-Type detectados  
✅ UTF-8 encoding en Content-Disposition
✅ CORS headers expuestos
✅ OpenAPI documentado como binario
✅ Funciones de preview implementadas

---

## 📚 Endpoints Principales

### Documentos
- `GET /expedientes/{id}/documentos` - Listar documentos
- `POST /expedientes/{id}/documentos` - Subir documento (nuevo)
- `GET /expedientes/{id}/documentos/{doc_id}/descargar` - **Descargar (mejorado)**
- `GET /expedientes/{id}/documentos/{doc_id}/preview` - **Previsualizar (nuevo)**

### Expedientes
- `GET /expedientes` - Listar expedientes
- `POST /expedientes` - Crear expediente
- `GET /expedientes/{id}` - Obtener detalle
- `PUT /expedientes/{id}` - Actualizar estado

### Evaluaciones
- `GET /evaluacion` - Listar evaluaciones
- `GET /evaluacion/mis-evaluaciones` - Mis evaluaciones (incluye `titulo_protocolo`)
- `POST /evaluacion` - Crear evaluación
- `PUT /evaluacion/{id}` - Completar evaluación

---

## ⚙️ Instalación y Ejecución

```bash
# Instalar dependencias
pip install -r requirements.txt

# Ejecutar servidor
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Ver API docs
http://localhost:8000/docs
```

---

## 📞 Para el Frontend

### Configuración de URLs

**Entorno de Producción (Render):**
- API Base: `https://comite-backend.onrender.com/api/v1`
- Docs (Swagger): `https://comite-backend.onrender.com/docs`
- ReDoc: `https://comite-backend.onrender.com/redoc`

**Configuración sugerida en Frontend (.env):**
```env

# Producción
REACT_APP_API_URL=https://comite-backend.onrender.com/api/v1
```

### Headers requeridos en todas las peticiones

```javascript
{
  'Authorization': `Bearer ${token}`,
  'Content-Type': 'application/json'
}
```

### Para descargar/previsualizar documentos

```javascript
// No necesitas Content-Type para estos endpoints
{
  'Authorization': `Bearer ${token}`
}
```

---

