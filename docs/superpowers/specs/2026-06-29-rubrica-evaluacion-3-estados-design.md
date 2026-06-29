# Diseño: Rúbrica de evaluación (20 pts) + 3 estados de dictamen

**Fecha:** 2026-06-29
**Proyecto:** Sistema Comité de Ética UCH (backend FastAPI + frontend Next.js)
**Estado:** Aprobado para implementación

## Contexto y problema

El sistema actual evalúa con un modelo **binario** que no refleja la decisión del
Comité ni el formato oficial de evaluación:

- `EstadoExpedienteEnum` no tiene "aprobado con observaciones" ni "no aprobado".
- `TipoDictamenEnum` solo permite `aprobado` / `observado`.
- `reportes/routes.py:69` declara explícitamente "sin desaprobado/rechazado".
- El modelo `Evaluacion` **no tiene rúbrica ni puntaje** (solo `nivel_riesgo`,
  `recommendation`, `observaciones`, `completa`).
- El dictamen se emite **manualmente** (el coordinador elige el tipo por query
  param) y exige **mínimo 2 evaluaciones** (`dictamen/routes.py:79`), con una
  vista de consolidación.

El formato oficial del Comité (`FORMATO DE EVALUACIÓN_PROYECTOS DE INVESTIGACIÓN`)
define **un solo revisor**, una **rúbrica de 7 criterios que suman 20 puntos**, y
un **dictamen de 3 estados** derivado del puntaje.

## Objetivo

Implementar el modelo real del Comité: **1 evaluador** llena una **rúbrica de 20
puntos** y el sistema **deriva automáticamente** el dictamen en **3 estados**.

## Rúbrica oficial (fuente de verdad)

| # | Criterio (`key`) | Pts máx |
|---|------------------|--------|
| 1 | Valor y pertinencia del estudio (`valor_pertinencia`) | 2 |
| 2 | Principios éticos (`principios_eticos`) | 4 |
| 3 | Consentimiento informado (`consentimiento_informado`) | 4 |
| 4 | Protección de participantes (`proteccion_participantes`) | 3 |
| 5 | Poblaciones vulnerables (si aplica) (`poblaciones_vulnerables`) | 2 |
| 6 | Confidencialidad y protección de datos (`confidencialidad_datos`) | 3 |
| 7 | Adecuación metodológica (`adecuacion_metodologica`) | 2 |
| | **Total** | **20** |

Cada criterio tiene `descripcion` (texto del formato), `puntaje` obtenido y una
`observacion` opcional. "Poblaciones vulnerables" se modela como criterio normal
0-2: si aplica y se cumple = 2, si no aplica = 0 (sin opción especial "N/A").

### Umbrales → resultado (texto oficial)

| Puntaje total | Resultado (`resultado` / `tipo_dictamen`) |
|---------------|-------------------------------------------|
| 17 – 20 | **Aprobado** (`aprobado`) |
| 13 – 16 | **Aprobado con observaciones** (`aprobado_observaciones`) |
| 0 – 12 | **No aprobado** (`no_aprobado`) |

Implicación aceptada: un proyecto sin poblaciones vulnerables tope en 18/20; igual
alcanza "Aprobado" (≥17), así que no bloquea.

## Modelo de datos (backend, sin Alembic → cambios aditivos)

### Catálogo en `app/models`
- `CRITERIOS_RUBRICA`: lista ordenada de los 7 criterios con
  `{key, nombre, descripcion, puntaje_max}`.
- `PUNTAJE_TOTAL_MAX = 20`.
- `resultado_por_puntaje(total: int) -> str`: aplica los umbrales y devuelve uno
  de `aprobado` / `aprobado_observaciones` / `no_aprobado`.

### Nueva tabla `evaluacion_criterios` (aditiva, segura en Aiven)
```
id              Integer PK
evaluacion_id   FK -> evaluaciones.id
criterio_key    String   # uno de CRITERIOS_RUBRICA
puntaje         Integer  # 0..puntaje_max
observacion     Text     # opcional
```
Relación: `Evaluacion.criterios = relationship(... cascade)`.

### Columnas nuevas en `Evaluacion`
- `puntaje_total Integer nullable` (calculado al completar).
- `resultado String(50) nullable` (uno de los 3 estados).

Se conservan `observaciones` (observaciones generales del Comité) y
`recommendation`. **Nota de despliegue:** agregar columnas a una tabla existente
en Aiven requiere migración manual (`ALTER TABLE`), no solo `create_all`.

### Enums
- `EstadoExpedienteEnum`: agregar `APROBADO_OBSERVACIONES = "aprobado_observaciones"`
  y `NO_APROBADO = "no_aprobado"` (ya existe `APROBADO = "aprobado"`).
- `TipoDictamenEnum`: pasar de 2 a 3 valores: `APROBADO`,
  `APROBADO_OBSERVACIONES`, `NO_APROBADO`.

## Lógica de negocio

1. **1 solo evaluador** por expediente. Se elimina el requisito de "mínimo 2
   evaluaciones completas" en `dictamen/routes.py`.
2. Al marcar la evaluación como `completa = True`:
   - Validar que exista un puntaje por cada criterio y que cada uno esté en
     `0..puntaje_max` (rechazo `400` si no).
   - `puntaje_total = sum(criterios)`.
   - `resultado = resultado_por_puntaje(puntaje_total)`.
   - Actualizar `Expediente.estado` al estado correspondiente
     (`aprobado` / `aprobado_observaciones` / `no_aprobado`).
3. **Dictamen automático**: `tipo_dictamen` se deriva de `Evaluacion.resultado`
   (ya no se pasa por query param). El PDF de dictamen se genera para los **3**
   resultados (no solo aprobado).
4. La **consolidación** queda obsoleta: la vista del coordinador pasa a revisar /
   emitir / firmar, sin promediar múltiples evaluaciones.

## API (backend)

- `GET /evaluacion/rubrica` → `{criterios: [...], puntaje_total_max: 20, umbrales: [...]}`
  para renderizar el formulario.
- `PUT /evaluacion/{id}` → acepta
  `{criterios: [{key, puntaje, observacion}], observaciones, completa}`.
  Al completar, calcula total/resultado y actualiza el expediente.
- `GET /evaluacion/{id}` → incluye `criterios`, `puntaje_total`, `resultado`.
- `dictamen` (`POST /`, `firmar`) → deriva resultado de la evaluación; permite los
  3 tipos; genera PDF en los 3 casos.
- `reportes/routes.py` → quitar la exclusión "sin desaprobado/rechazado"; incluir
  `no_aprobado` en los resultados.

## Frontend

- **Formulario de rúbrica** (rol evaluador): 7 criterios con su descripción y
  máximo, input de puntaje (0..max) y observación por criterio, observaciones
  generales, **total en vivo** y **badge del resultado previsto** según umbrales.
- `components/shared/status-badge.tsx` + `types/domain.ts`: agregar los 3 estados
  con colores (Aprobado = verde, Aprobado con observaciones = ámbar, No aprobado =
  rojo).
- `services/evaluacion` y `services/dictamen`: alinear tipos y payloads.
- Vista de **consolidación** del coordinador: ajustar al modelo de 1 evaluador
  (revisar/emitir/firmar, sin consolidar).

## Pruebas

- **Umbrales** (casos borde): total 12 → no_aprobado, 13 → aprobado_observaciones,
  16 → aprobado_observaciones, 17 → aprobado, 20 → aprobado.
- **Validación**: puntaje > max o < 0 → `400`; criterio faltante → `400`.
- **Transición de estado**: completar evaluación setea el `Expediente.estado`
  correcto.
- **Dictamen automático**: `tipo_dictamen` coincide con `resultado`; ya no exige 2
  evaluaciones.

## Fuera de alcance (YAGNI)

- Promediar / consolidar múltiples evaluadores (se descarta el modelo de 2).
- Recalcular umbrales proporcionalmente cuando "poblaciones vulnerables" no aplica
  (se decidió 0 fijo, total siempre /20).
- Cambios al flujo de cambio de título (ya implementado); solo se beneficia de los
  nuevos estados cuando corresponda.
