-- Migración: rúbrica de evaluación (20 pts) + 3 estados
-- Aplicar en Aiven (PostgreSQL). Idempotente.

-- Columnas nuevas en evaluaciones
ALTER TABLE evaluaciones ADD COLUMN IF NOT EXISTS puntaje_total INTEGER;
ALTER TABLE evaluaciones ADD COLUMN IF NOT EXISTS resultado VARCHAR(50);

-- Tabla de criterios de la rúbrica (1 fila por criterio por evaluación)
CREATE TABLE IF NOT EXISTS evaluacion_criterios (
    id SERIAL PRIMARY KEY,
    evaluacion_id INTEGER NOT NULL REFERENCES evaluaciones(id),
    criterio_key VARCHAR(50) NOT NULL,
    puntaje INTEGER NOT NULL DEFAULT 0,
    observacion TEXT
);
CREATE INDEX IF NOT EXISTS ix_evaluacion_criterios_id ON evaluacion_criterios (id);
