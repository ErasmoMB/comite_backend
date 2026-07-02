# Chat solicitante ↔ Secretaría — Design

**Fecha:** 2026-07-02 · **Aprobado por:** usuario (backend owner)

## Objetivo

Chat básico de texto, 1-a-1, entre cada solicitante (estudiante pregrado/postgrado o
investigador) y la Secretaría del Comité (bandeja compartida del rol). Para dudas y
coordinación directa; los documentos siguen yendo por el flujo formal de expedientes.

## Decisiones (confirmadas con el usuario)

| Decisión | Elección |
|---|---|
| Organización | **Un solo hilo por persona** (el hilo = el solicitante) |
| Tiempo real | **Polling** con TanStack Query (hilo 4s, bandeja 10s, badges 20s) — sin WebSockets |
| Bandeja | **Compartida del rol**: cualquier `secretaria` (o `administrador`) ve y responde todo; el solicitante ve "Secretaría del Comité" |
| Contenido | **Solo texto** (máx. 2000 caracteres) |
| Acceso | Cualquier solicitante con cuenta (tenga o no proyectos) |
| Iniciar | El solicitante **y también la secretaría** (elige de la lista de solicitantes) |
| Datos visibles para secretaría | Nombre completo + `codigo_estudiante` (investigador no tiene código → no se muestra) + rol + email |

## Modelo de datos (Enfoque A: una sola tabla)

```python
class MensajeChat(Base):
    __tablename__ = "mensajes_chat"
    id             = Column(Integer, primary_key=True, index=True)
    solicitante_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)  # dueño del hilo
    autor_id       = Column(Integer, ForeignKey("users.id"), nullable=False)  # quién escribió
    texto          = Column(Text, nullable=False)
    leido          = Column(Boolean, default=False)  # leído por el destinatario
    created_at     = Column(DateTime, server_default=func.now())
```

- `autor_id == solicitante_id` → escribió el solicitante; distinto → escribió secretaría.
- `leido` se marca automáticamente al traer el hilo desde el lado receptor.
- Tabla aditiva: la crea `create_all` al arrancar. SQL de referencia en
  `docs/migraciones/2026-07-02-chat.sql`.
- Se rechazó el modelo de dos tablas (`conversaciones`+`mensajes`): metadata innecesaria hoy
  (YAGNI); migrar después es trivial.

## Endpoints (`app/api/chat/routes.py`, prefijo `/api/v1/chat`)

Las rutas fijas se definen ANTES de `/{solicitante_id}` (pitfall conocido del codebase).

**Solicitante** (rol en `ROLES_AUTO_REGISTRO`; otro rol → 403):
- `GET /chat/mios` → mensajes del hilo propio (asc) y marca leídos los de secretaría.
- `POST /chat/mios` `{texto}` → envía mensaje.
- `GET /chat/mios/no-leidos` → `{no_leidos: n}`.

**Secretaría** (rol `secretaria` o `administrador`; otro rol → 403):
- `GET /chat/conversaciones` → bandeja agrupada por solicitante: nombre, código, rol,
  último mensaje, fecha, no-leídos; ordenada por mensaje más reciente.
- `GET /chat/solicitantes` → todos los usuarios con rol solicitante (para iniciar chat).
- `GET /chat/no-leidos` → total de no-leídos de la bandeja.
- `GET /chat/{solicitante_id}` → hilo completo y marca leídos los del solicitante.
- `POST /chat/{solicitante_id}` `{texto}` → responde o inicia conversación.

Validaciones: texto no vacío tras `strip()` y ≤2000 chars (400); `solicitante_id` debe
existir y tener rol solicitante (404).

## Frontend

- **Tipos** `types/api/chat.ts`, **service** `services/chat.service.ts`, **hooks** en
  `hooks/use-comite-query.ts` con `refetchInterval` (4s/10s/20s), siguiendo patrones existentes.
- **Componente compartido** de hilo (burbujas propias a la derecha, del otro lado a la
  izquierda, auto-scroll al final, textarea con Enter para enviar).
- **Solicitante:** nav "Consultas" → `/investigador/consultas` (vista de un hilo).
- **Secretaría:** nav "Chat" → `/secretaria/chat`, dos paneles: lista de conversaciones
  (nombre, código o "Investigador", snippet, badge no-leídos) + botón "Nueva conversación"
  (diálogo con buscador de solicitantes) | hilo activo con cabecera de datos del solicitante.

## Errores y bordes

- Hilo vacío → estado vacío amable.
- Error de polling → reintento silencioso de TanStack Query; error visible solo al fallar
  el envío (toast; el texto no se pierde del input).
- Investigador sin código → la línea de código no se muestra.

## Testing

- **Backend:** pytest (harness SQLite en memoria existente): permisos por rol, envío/lectura,
  marcado de leídos, bandeja con no-leídos y orden, secretaría inicia conversación,
  validación de texto.
- **Frontend:** `tsc --noEmit` + verificación E2E en navegador con ambos roles contra Aiven.

## Fuera de alcance (v1)

Adjuntos, WebSockets, integración con la campana de notificaciones, archivar/buscar,
indicador "escribiendo…". Todo agregable sin rehacer el modelo.
