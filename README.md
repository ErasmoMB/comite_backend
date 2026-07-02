# Comité de Ética — Backend (FastAPI)

## ⚠️ Base de datos: SIEMPRE Aiven (PostgreSQL)

Este proyecto **trabaja exclusivamente con la base de datos de Aiven** (PostgreSQL en la
nube). **Nunca** se debe usar la base SQLite local (`comite_new_test.db`): tiene datos
desactualizados y *drift* de esquema, y mezclar ambas causa confusión (datos que
aparecen/desaparecen entre arranques).

### Cómo se garantiza
- La conexión sale de `backend/.env` → variable `DATABASE_URL` (formato `postgresql://...`,
  **no** `postgres://`). Ese archivo está en `.gitignore` (contiene credenciales, no subir).
- `app/db/database.py` tiene un **candado**: si `DATABASE_URL` apunta a SQLite, el backend
  **se niega a arrancar** con un error claro. La única excepción es correr los tests
  (`conftest.py` exporta `ALLOW_SQLITE=1` para usar SQLite en memoria, aislado de Aiven).
- Al arrancar, el backend imprime en consola contra qué base se conectó, por ejemplo:
  `[DB] Conectado a: comite-comite.a.aivencloud.com:23283/defaultdb`
  → **verifica siempre esa línea** al levantar.

Si ves el error del candado, es porque falta `backend/.env` o su `DATABASE_URL`. Configúralo
con la URI de Aiven y vuelve a arrancar.

---

## 🚀 Cómo levantar

> **Importante:** el proceso debe ejecutarse **desde la carpeta `backend/`**. Los PDFs de
> rúbrica/dictamen se guardan con rutas relativas (`uploads/...`) y `FileResponse` las
> resuelve contra el directorio de trabajo. Si arrancas desde otra carpeta (p. ej. la raíz
> del repo), las **descargas darán 404** aunque el archivo exista.

### Windows (PowerShell)
```powershell
cd C:\Users\...\comite\backend
$env:PYTHONPATH = (Get-Location).Path
.\env\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8001
```

- Puerto **8001** (el 8000 lo ocupa otra app local).
- Verifica la línea `[DB] Conectado a: ...aivencloud.com...` al arrancar.
- Docs interactivos: http://localhost:8001/docs

### Sembrar credenciales demo (idempotente)
```powershell
.\env\Scripts\python.exe seed_demo.py
```
Todas con password `password`: `pregrado@uch.edu.pe`, `postgrado@uch.edu.pe`,
`investigador@uch.edu.pe`, `secretaria@uch.edu.pe`, `coordinador@uch.edu.pe`,
`evaluador@uch.edu.pe`, `admin@uch.edu.pe`.

---

## 📌 Funcionalidades principales

- **Auth:** login unificado (`POST /auth/login`, OAuth2 form). Auto-registro solo para
  roles solicitantes (`estudiante_pregrado`, `estudiante_postgrado`, `investigador`);
  los roles internos los crea el admin.
- **Expedientes:** envío dinámico por modalidad (pregrado/postgrado/interno), checklist
  de requisitos, bloqueo si está incompleto, código anual `N-AÑO` al enviar, cambio de
  título solo para proyectos aprobados.
- **Evaluación con rúbrica (20 pts):** 7 criterios oficiales, 1 evaluador por expediente.
  Al completar (`PUT /evaluacion/{id}`) se calcula el puntaje y el resultado
  (0-12 no_aprobado / 13-16 aprobado_observaciones / 17-20 aprobado), se actualiza el
  estado del expediente y se **generan los PDFs automáticamente**: aprobado → dictamen;
  aprobado_observaciones → rúbrica + dictamen; no_aprobado → rúbrica. También se envía
  email a los autores con los PDFs adjuntos.
- **Descargas:** evaluador vía `GET /evaluacion/{id}/descargar-rubrica|descargar-dictamen`;
  solicitante vía `GET /expedientes/{id}/descargar-evaluacion/{informe|dictamen}`.
- **Chat solicitante ↔ Secretaría** (`/api/v1/chat`): un hilo por solicitante, bandeja
  compartida del rol secretaría (el admin también puede atender), solo texto (máx. 2000).
  - Solicitante: `GET/POST /chat/mios`, `GET /chat/mios/no-leidos`.
  - Secretaría: `GET /chat/conversaciones` (bandeja con nombre/código/no-leídos),
    `GET /chat/solicitantes`, `GET /chat/no-leidos`, `GET/POST /chat/{solicitante_id}`.
  - Los mensajes se marcan leídos al abrir el hilo. El frontend refresca por polling.
  - Spec: `docs/superpowers/specs/2026-07-02-chat-secretaria-design.md`.

## 🧪 Tests
```powershell
cd backend
$env:PYTHONPATH = (Get-Location).Path
.\env\Scripts\python.exe -m pytest -v
```
Los tests usan SQLite en memoria (no tocan Aiven) gracias a `ALLOW_SQLITE=1` en `conftest.py`.

---

## 🔧 Configuración
Ver `app/core/config.py`. El fallback por defecto a SQLite existe solo como último recurso
y queda **bloqueado por el candado** descrito arriba salvo `ALLOW_SQLITE=1`.
