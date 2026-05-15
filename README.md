# Backend - Comité de Ética

## Actualizaciones Recientes

### 14/05/2026 - Correcciones de observaciones del frontend

1. **GET /expedientes/{id}/documentos**
   - Endpoint agregado para listar documentos de un expediente
   - Retorna lista de documentos asociados al expediente
   - Validación de acceso: investigador solo puede ver sus propios expedientes

2. **Validaciones explícitas de documentos en OpenAPI**
   - Tipos MIME permitidos: PDF, DOC, DOCX, XLS, XLSX, TXT
   - Extensiones permitidas: .pdf, .doc, .docx, .xls, .xlsx, .txt
   - Tamaño máximo: 10 MB
   - Documentado en el endpoint de upload de documentos

3. **Endpoint de subsanación documentado**
   - Endpoint: `POST /expedientes/{id}/subsanacion`
   - Permite al investigador responder a las observaciones de evaluadores
   - Solo funciona cuando el expediente está en estado SUBSANACION

## Endpoints de Expedientes

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/expedientes/` | Lista todos los expedientes |
| GET | `/expedientes/{id}` | Obtiene un expediente por ID |
| POST | `/expedientes/` | Crea un nuevo expediente |
| PUT | `/expedientes/{id}` | Actualiza un expediente |
| POST | `/expedientes/{id}/enviar` | Envía formalmente el expediente |
| GET | `/expedientes/{id}/documentos` | Lista documentos del expediente |
| POST | `/expedientes/{id}/documentos` | Sube un documento al expediente |
| POST | `/expedientes/{id}/subsanacion` | Registra subsanación por observación |
| GET | `/expedientes/{id}/bitacora` | Ver bitácora del expediente |
| GET | `/expedientes/{id}/historial` | Ver historial de estados |