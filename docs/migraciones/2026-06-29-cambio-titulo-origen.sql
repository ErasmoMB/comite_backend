-- Migración: vincular cambio de título a su proyecto de origen (aprobado).
-- Aplicar en Aiven (PostgreSQL). Idempotente.

ALTER TABLE expedientes ADD COLUMN IF NOT EXISTS proyecto_origen_id INTEGER REFERENCES expedientes(id);
