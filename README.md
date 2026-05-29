# Comité de Ética - Backend

## 📋 Estado de Correcciones

### ✅ Corrección: Firma de Dictamen - SOLUCIONADO

**Fecha:** 28/05/2026

**Problema identificado:**
- Error al firmar dictamen: `generar_pdf_dictamen() got an unexpected keyword argument 'tipo_dictamen'`
- Los parámetros en la llamada a `generar_pdf_dictamen()` no coincidían con la firma de la función

**Corrección aplicada:**
- Removido parámetro `tipo_dictamen` (no existe en función)
- Corregidos nombres de parámetros:
  - `titulo_protocolo` → `titulo`
  - `investigadores` → `investigador_nombre`
  - `fecha_firma` → `dictamen_fecha`

**Archivo modificado:**
- `app/api/dictamen/routes.py` (función `firmar_dictamen`)

**Estado:** 🟢 Listo para pruebas

---

## 📝 Pruebas Recomendadas (Frontend)

1. **POST** `/api/v1/dictamen/{dictamen_id}/firmar`
   - Debe responder con dictamen firmado
   - Campo `archivo_url` debe estar poblado

2. **GET** `/api/v1/dictamen/{dictamen_id}/descargar`
   - Debe servir el PDF correctamente

---

## 🔧 Configuración

Ver archivos de configuración en `app/core/config.py`
