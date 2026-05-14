# Comité de Ética - Backend

Backend FastAPI para el sistema de Comité de Ética de la Universidad.

## 🚀 Características Implementadas

### ✅ 1. Campo `recommendation` en Evaluaciones

**Descripción:** Se agregó el campo `recommendation` a las evaluaciones para que los evaluadores puedan proporcionar recomendaciones específicas.

**Endpoints afectados:**
- `POST /api/v1/evaluacion` - Crear evaluación
- `PUT /api/v1/evaluacion/{evaluacion_id}` - Actualizar evaluación
- `GET /api/v1/evaluacion/mis-evaluaciones` - Obtener evaluaciones del usuario

**Schema:**
```python
class EvaluacionResponse(BaseModel):
    id: int
    expediente_id: int
    evaluador_id: int
    nivel_riesgo: str
    recommendation: Optional[str]  # ✅ NUEVO
    observaciones: Optional[str]
    completa: bool
```

**Validación:** ✅ Probado en TEST 4

---

### ✅ 2. Campos Extendidos en Dictamenes

**Descripción:** Se extendió el modelo `DictamenResponse` con campos adicionales para metadatos del dictamen.

**Campos nuevos:**
- `fecha_firma` - Fecha cuando se firmó el dictamen
- `fecha_emision` - Fecha de emisión del dictamen
- `archivo_url` - URL del archivo del dictamen (opcional)

**Schema:**
```python
class DictamenResponse(BaseModel):
    id: int
    expediente_id: int
    numero_dictamen: Optional[str]
    tipo_dictamen: Optional[str]
    contenido: str
    firmado: bool
    fecha_emision: Optional[datetime] = None  # ✅ NUEVO
    fecha_firma: Optional[datetime] = None    # ✅ NUEVO
    archivo_url: Optional[str] = None         # ✅ NUEVO
    created_at: datetime
```

**Endpoints:**
- `POST /api/v1/dictamen` - Crear dictamen
- `POST /api/v1/dictamen/{dictamen_id}/firmar` - Firmar dictamen con timestamp

**Validación:** ✅ Probado en TEST 5 - Dictamen creado y firmado con timestamps

---

### ✅ 3. Validaciones de Documentos

**Descripción:** Se implementó validación integral de documentos con restricciones de MIME type y tamaño.

**Validaciones implementadas:**

1. **Tipos MIME permitidos:**
   - `application/pdf` - PDF
   - `application/msword` - DOC
   - `application/vnd.openxmlformats-officedocument.wordprocessingml.document` - DOCX
   - `application/vnd.ms-excel` - XLS
   - `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` - XLSX
   - `text/plain` - TXT

2. **Límite de tamaño:** 10 MB máximo

3. **Sanitización de nombres:** UUID para evitar colisiones

**Endpoint:**
- `POST /api/v1/expedientes/{expediente_id}/documentos` - Upload con validación

**Validación:** ✅ Probado en TEST 2
- ✅ Acepta archivos válidos
- ✅ Rechaza archivos > 10MB
- ✅ Rechaza tipos MIME no permitidos

---

### ✅ 4. Endpoint de Subsanación

**Descripción:** Nuevo endpoint que permite a investigadores responder a observaciones del comité.

**Endpoint:**
```
POST /api/v1/expedientes/{expediente_id}/subsanacion
```

**Request:**
```json
{
  "observaciones": "Se han corregido los puntos señalados..."
}
```

**Response:**
```json
{
  "mensaje": "Subsanación registrada correctamente. Pendiente de revisión coordinada.",
  "expediente_id": 16,
  "estado": "subsanacion",
  "fecha_subsanacion": "2026-05-14T03:51:41.648828"
}
```

**Características:**
- Registra la subsanación en la bitácora
- Cambia estado del expediente a `subsanacion`
- Retorna timestamp de registro

**Validación:** ✅ Probado en TEST 6

---

### ✅ 5. Schemas Tipados para Endpoints de IA

**Descripción:** Se definieron schemas claros y tipados para todos los endpoints de IA con respuestas estructuradas.

**Endpoints:**

1. **GET /api/v1/ia/preanalisis/{expediente_id}**
```python
class IAAnalisisResponse(BaseModel):
    analisis: str
    nivel_riesgo: str
    recomendaciones: List[str]
    confianza: float
    factores_clave: List[str]
```

2. **GET /api/v1/ia/detectar-inconsistencias/{expediente_id}**
```python
class IAInconsistenciasResponse(BaseModel):
    inconsistencias: List[str]
    cantidad: int
    mensaje: str
```

3. **GET /api/v1/ia/detectar-riesgos/{expediente_id}**
```python
class IARiesgosResponse(BaseModel):
    nivel_riesgo: str
    factores: List[str]
    recomendaciones: List[str]
    mensaje: str
```

**Validación:** ✅ Probado en TEST 7 - Todos retornan status 200 con schemas correctos

**Documentación OpenAPI:** Disponible en http://localhost:8000/docs

---

### ✅ 6. Schemas Tipados para Endpoints de Reportes

**Descripción:** Se definieron schemas claros y tipados para todos los endpoints de reportes.

**Endpoints:**

1. **GET /api/v1/reportes/expedientes-por-estado**
```python
class EstadisticasExpediente(BaseModel):
    total: int
    por_estado: Dict[str, int]
```

2. **GET /api/v1/reportes/tiempos-atencion**
```python
class ReporteTiempoAtencion(BaseModel):
    expediente_id: int
    codigo: str
    dias: int
    estado: str
```

3. **GET /api/v1/reportes/carga-evaluadores**
```python
class ReporteCargaEvaluadores(BaseModel):
    evaluador_id: int
    nombre: Optional[str]
    total_evaluaciones: int
```

4. **GET /api/v1/reportes/resultados-emitidos**
```python
class ReporteResultados(BaseModel):
    tipo: str
    total: int
```

5. **GET /api/v1/reportes/resumen**
```python
class ReporteGeneralResponse(BaseModel):
    fecha_generacion: datetime
    expedientes: EstadisticasExpediente
    evaluadores: Dict[str, Any]
    tiempos_atencion: List[ReporteTiempoAtencion]
    carga_evaluadores: List[ReporteCargaEvaluadores]
    resultados: List[ReporteResultados]
    archivo_url: Optional[str]
```

**Validación:** ✅ Probado en TEST 8 - Todos los endpoints retornan status 200 con schemas correctos

**Documentación OpenAPI:** Disponible en http://localhost:8000/docs

---

## 📊 Resultados de Testing

### Test Suite: `test_6_features.py`

Todos los tests pasan correctamente:

```
✅ TEST 1: Crear Expediente - PASSED
✅ TEST 2: Validaciones de Documento - PASSED
✅ TEST 3: Asignar Evaluadores - PASSED
✅ TEST 4: Crear y Completar Evaluación - PASSED
✅ TEST 5: Crear y Firmar Dictamen - PASSED
✅ TEST 6: Endpoint de Subsanación - PASSED
✅ TEST 7: Endpoints de IA con Schemas Tipados - PASSED
✅ TEST 8: Endpoints de Reportes con Schemas Tipados - PASSED
```

---

## 🔧 Stack Técnico

- **Framework:** FastAPI 0.104.1
- **ORM:** SQLAlchemy 2.0.36
- **Base de Datos:** PostgreSQL 18
- **Autenticación:** JWT con python-jose
- **Validación:** Pydantic V2
- **Seguridad:** bcrypt para contraseñas

---

## 📖 Documentación OpenAPI

Accede a la documentación interactiva en:

```
http://localhost:8000/api/v1/docs
```

Todos los endpoints están documentados con:
- Descripciones detalladas
- Esquemas de request/response
- Ejemplos de uso
- Códigos de status esperados

---

## ✨ Notas Importantes

### Migraciones de Base de Datos

Se agregaron nuevas columnas a la tabla `dictamines`:
- `fecha_firma` - Para registrar cuándo se firmó
- `archivo_url` - Para almacenar URL del archivo del dictamen

Ejecutar antes de usar:
```bash
python migrate_dictamines.py
```

### Validaciones de Seguridad

- ✅ Solo coordinadores pueden crear dictámenes
- ✅ Solo el mismo evaluador puede actualizar su evaluación
- ✅ Solo investigador propietario puede enviar subsanación
- ✅ Validación MIME type en uploads
- ✅ Límite de tamaño en documentos (10MB)

---

## 🚀 Próximos Pasos

- [ ] Integración con modelos de IA reales (OpenAI, Claude)
- [ ] Sistema de notificaciones por email
- [ ] Generación de PDFs para dictámenes
- [ ] Sistema de auditoría mejorado
- [ ] Caché para reportes

---

**Última actualización:** 14 de Mayo, 2026
**Estado:** ✅ Producción Ready - Todas las 6 características implementadas y validadas
