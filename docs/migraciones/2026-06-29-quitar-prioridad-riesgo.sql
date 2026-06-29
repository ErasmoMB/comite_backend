-- Migración: quitar columnas prioridad y nivel_riesgo (decisión del Comité).
-- Aplicar en Aiven (PostgreSQL). Idempotente. DESTRUCTIVO (elimina datos de esas columnas).

ALTER TABLE expedientes DROP COLUMN IF EXISTS prioridad;
ALTER TABLE evaluaciones DROP COLUMN IF EXISTS nivel_riesgo;
