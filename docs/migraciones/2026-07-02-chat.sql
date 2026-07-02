-- Chat solicitante <-> Secretaría (spec: 2026-07-02-chat-secretaria-design.md)
-- Tabla ADITIVA: la crea automáticamente Base.metadata.create_all al arrancar el backend.
-- Este SQL es solo de referencia/manual por consistencia con las demás migraciones.

CREATE TABLE IF NOT EXISTS mensajes_chat (
    id SERIAL PRIMARY KEY,
    solicitante_id INTEGER NOT NULL REFERENCES users(id),
    autor_id INTEGER NOT NULL REFERENCES users(id),
    texto TEXT NOT NULL,
    leido BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_mensajes_chat_solicitante_id ON mensajes_chat (solicitante_id);
