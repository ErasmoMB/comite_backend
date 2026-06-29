# Rúbrica de evaluación (20 pts) + 3 estados — Backend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Que un único evaluador llene una rúbrica oficial de 7 criterios (suma 20) y el backend derive automáticamente el dictamen en 3 estados (Aprobado / Aprobado con observaciones / No aprobado).

**Architecture:** Catálogo de criterios + función de umbrales en `app/models`; nueva tabla aditiva `evaluacion_criterios`; columnas `puntaje_total`/`resultado` en `Evaluacion`; al completar la evaluación se calcula total → resultado → estado del expediente; el dictamen deriva su tipo del resultado. Se elimina el requisito de 2 evaluaciones y la consolidación.

**Tech Stack:** FastAPI 0.115, SQLAlchemy 2.0, Pydantic 2.9, pytest (nuevo), SQLite en memoria para tests.

## Global Constraints

- Sin Alembic: el esquema se crea con `Base.metadata.create_all`. La nueva tabla `evaluacion_criterios` es aditiva (segura). Las dos columnas nuevas en `evaluaciones` requieren `ALTER TABLE` manual en Aiven (ver Task 9, no automatizable).
- Columna real del título del expediente: `Expediente.titulo_protocolo` (NO `titulo_proyecto`). Usar ese nombre.
- Valores canónicos de resultado/estado/dictamen (strings exactos, en minúscula): `"aprobado"`, `"aprobado_observaciones"`, `"no_aprobado"`.
- Umbrales: `17-20 → aprobado`, `13-16 → aprobado_observaciones`, `0-12 → no_aprobado`.
- Criterios y puntajes máximos (keys exactas): `valor_pertinencia`=2, `principios_eticos`=4, `consentimiento_informado`=4, `proteccion_participantes`=3, `poblaciones_vulnerables`=2, `confidencialidad_datos`=3, `adecuacion_metodologica`=2 (total 20).
- Trabajar en la rama `feat/rubrica-3-estados`. Comandos se ejecutan desde `backend/` con el venv activo (`backend/env/`) y `PYTHONPATH` = carpeta `backend`.

---

### Task 1: Harness de tests + catálogo de rúbrica y función de umbrales

**Files:**
- Modify: `requirements.txt`
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`
- Create: `tests/test_rubrica.py`
- Modify: `app/models/__init__.py` (agregar catálogo + función al final del archivo)

**Interfaces:**
- Produces:
  - `app.models.CRITERIOS_RUBRICA: list[dict]` con items `{"key": str, "nombre": str, "descripcion": str, "puntaje_max": int}`.
  - `app.models.PUNTAJE_TOTAL_MAX: int = 20`.
  - `app.models.resultado_por_puntaje(total: int) -> str` → uno de `"aprobado" | "aprobado_observaciones" | "no_aprobado"`.

- [ ] **Step 1: Agregar pytest a requirements**

En `requirements.txt` añadir al final:
```
pytest==8.3.4
```

- [ ] **Step 2: Instalar pytest**

Run: `pip install pytest==8.3.4`
Expected: instala correctamente (httpx ya está para TestClient).

- [ ] **Step 3: Crear `tests/__init__.py` vacío**

Archivo vacío (marca el paquete de tests).

- [ ] **Step 4: Crear `tests/conftest.py`**

```python
import os
# Forzar SQLite en memoria ANTES de importar la app (evita conectar a Aiven).
os.environ["DATABASE_URL"] = "sqlite://"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.database import Base, get_db
from app.api.auth.routes import get_current_user
from app.main import app
import app.models as models  # noqa: F401  (registra todos los modelos en Base)

engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture
def db():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(db):
    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


def make_user(db, rol, email=None):
    """Crea y persiste un usuario con el rol dado."""
    user = models.User(
        email=email or f"{rol}@test.com",
        password_hash="x",
        nombre="Test",
        apellido=rol,
        rol=rol,
        activo=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def auth_as(user):
    """Devuelve un override de get_current_user que retorna `user`."""
    def _override():
        return user
    return _override
```

- [ ] **Step 5: Escribir el test de catálogo y umbrales (falla)**

Create `tests/test_rubrica.py`:
```python
import pytest
from app.models import CRITERIOS_RUBRICA, PUNTAJE_TOTAL_MAX, resultado_por_puntaje


def test_catalogo_suma_20_y_tiene_7_criterios():
    assert len(CRITERIOS_RUBRICA) == 7
    assert sum(c["puntaje_max"] for c in CRITERIOS_RUBRICA) == 20
    assert PUNTAJE_TOTAL_MAX == 20
    keys = {c["key"] for c in CRITERIOS_RUBRICA}
    assert keys == {
        "valor_pertinencia", "principios_eticos", "consentimiento_informado",
        "proteccion_participantes", "poblaciones_vulnerables",
        "confidencialidad_datos", "adecuacion_metodologica",
    }


@pytest.mark.parametrize("total,esperado", [
    (0, "no_aprobado"), (12, "no_aprobado"),
    (13, "aprobado_observaciones"), (16, "aprobado_observaciones"),
    (17, "aprobado"), (20, "aprobado"),
])
def test_umbrales(total, esperado):
    assert resultado_por_puntaje(total) == esperado
```

- [ ] **Step 6: Correr el test (debe fallar)**

Run: `pytest tests/test_rubrica.py -v`
Expected: FAIL con `ImportError: cannot import name 'CRITERIOS_RUBRICA'`.

- [ ] **Step 7: Implementar catálogo y función**

Al final de `app/models/__init__.py` agregar:
```python
CRITERIOS_RUBRICA = [
    {"key": "valor_pertinencia", "nombre": "Valor y pertinencia del estudio",
     "descripcion": "El proyecto presenta una justificación clara y una contribución académica y social relevante. Cuenta con los recursos necesarios para su implementación, incluyendo financiamiento, infraestructura, tiempo y personal capacitado.",
     "puntaje_max": 2},
    {"key": "principios_eticos", "nombre": "Principios éticos",
     "descripcion": "Respeta los principios de autonomía, beneficencia, no maleficencia y justicia.",
     "puntaje_max": 4},
    {"key": "consentimiento_informado", "nombre": "Consentimiento informado",
     "descripcion": "El proceso de información y consentimiento es adecuado, claro y voluntario. Presenta el anexo correspondiente.",
     "puntaje_max": 4},
    {"key": "proteccion_participantes", "nombre": "Protección de participantes",
     "descripcion": "Identifica riesgos y establece medidas de protección para los participantes.",
     "puntaje_max": 3},
    {"key": "poblaciones_vulnerables", "nombre": "Poblaciones vulnerables (si aplica)",
     "descripcion": "El proyecto contempla medidas especiales para proteger a poblaciones vulnerables (niños, gestantes, personas con enfermedades mentales o discapacidades, comunidades no familiarizadas con conceptos médicos, personas con libertad restringida). Si no aplica, 0 puntos.",
     "puntaje_max": 2},
    {"key": "confidencialidad_datos", "nombre": "Confidencialidad y protección de datos",
     "descripcion": "Garantiza privacidad, anonimato o confidencialidad de la información.",
     "puntaje_max": 3},
    {"key": "adecuacion_metodologica", "nombre": "Adecuación metodológica",
     "descripcion": "La metodología es robusta, clara y científicamente válida, coherente con los objetivos y no expone innecesariamente a los participantes.",
     "puntaje_max": 2},
]

PUNTAJE_TOTAL_MAX = 20

CRITERIOS_MAX_POR_KEY = {c["key"]: c["puntaje_max"] for c in CRITERIOS_RUBRICA}


def resultado_por_puntaje(total: int) -> str:
    """Deriva el resultado del dictamen según el puntaje total (0-20)."""
    if total >= 17:
        return "aprobado"
    if total >= 13:
        return "aprobado_observaciones"
    return "no_aprobado"
```

- [ ] **Step 8: Correr el test (debe pasar)**

Run: `pytest tests/test_rubrica.py -v`
Expected: PASS (7 casos + 1).

- [ ] **Step 9: Commit**

```bash
git add requirements.txt tests/__init__.py tests/conftest.py tests/test_rubrica.py app/models/__init__.py
git commit -m "feat(eval): catálogo de rúbrica + umbrales + harness de tests"
```

---

### Task 2: Enums de estado y dictamen (3 estados)

**Files:**
- Modify: `app/models/__init__.py:37` (EstadoExpedienteEnum) y `:169` (TipoDictamenEnum)
- Test: `tests/test_enums.py`

**Interfaces:**
- Produces:
  - `EstadoExpedienteEnum.APROBADO_OBSERVACIONES = "aprobado_observaciones"`, `EstadoExpedienteEnum.NO_APROBADO = "no_aprobado"`.
  - `TipoDictamenEnum.APROBADO_OBSERVACIONES = "aprobado_observaciones"`, `TipoDictamenEnum.NO_APROBADO = "no_aprobado"` (se elimina `OBSERVADO`).

- [ ] **Step 1: Escribir el test (falla)**

Create `tests/test_enums.py`:
```python
from app.models import EstadoExpedienteEnum, TipoDictamenEnum


def test_estados_nuevos():
    assert EstadoExpedienteEnum.APROBADO.value == "aprobado"
    assert EstadoExpedienteEnum.APROBADO_OBSERVACIONES.value == "aprobado_observaciones"
    assert EstadoExpedienteEnum.NO_APROBADO.value == "no_aprobado"


def test_tipos_dictamen():
    valores = {t.value for t in TipoDictamenEnum}
    assert valores == {"aprobado", "aprobado_observaciones", "no_aprobado"}
```

- [ ] **Step 2: Correr (debe fallar)**

Run: `pytest tests/test_enums.py -v`
Expected: FAIL con `AttributeError: APROBADO_OBSERVACIONES`.

- [ ] **Step 3: Implementar — EstadoExpedienteEnum**

En `app/models/__init__.py` reemplazar el cuerpo de `EstadoExpedienteEnum` (líneas 37-43) por:
```python
class EstadoExpedienteEnum(str, enum.Enum):
    BORRADOR = "borrador"
    ENVIADO = "enviado"
    EN_REVISION = "en_revision"
    SUBSANACION = "subsanacion"
    APROBADO = "aprobado"
    APROBADO_OBSERVACIONES = "aprobado_observaciones"
    NO_APROBADO = "no_aprobado"
    ARCHIVADO = "archivado"
```

- [ ] **Step 4: Implementar — TipoDictamenEnum**

Reemplazar el cuerpo de `TipoDictamenEnum` (líneas 169-172) por:
```python
class TipoDictamenEnum(str, enum.Enum):
    """Estados permitidos para dictamen: aprobado, aprobado con observaciones o no aprobado."""
    APROBADO = "aprobado"
    APROBADO_OBSERVACIONES = "aprobado_observaciones"
    NO_APROBADO = "no_aprobado"
```

- [ ] **Step 5: Correr (debe pasar)**

Run: `pytest tests/test_enums.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add app/models/__init__.py tests/test_enums.py
git commit -m "feat(eval): enums de expediente y dictamen con 3 estados"
```

---

### Task 3: Modelo — tabla `evaluacion_criterios` + columnas en `Evaluacion`

**Files:**
- Modify: `app/models/__init__.py` (clase `Evaluacion` ~línea 275 y nueva clase)
- Test: `tests/test_modelo_criterios.py`

**Interfaces:**
- Produces:
  - Clase `EvaluacionCriterio` (tabla `evaluacion_criterios`): `id`, `evaluacion_id` (FK), `criterio_key` (String), `puntaje` (Integer), `observacion` (Text).
  - `Evaluacion.puntaje_total` (Integer, nullable), `Evaluacion.resultado` (String(50), nullable), `Evaluacion.criterios` (relationship lista, cascade delete-orphan).

- [ ] **Step 1: Escribir el test (falla)**

Create `tests/test_modelo_criterios.py`:
```python
from tests.conftest import make_user
from app.models import Expediente, Evaluacion, EvaluacionCriterio


def test_crear_evaluacion_con_criterios(db):
    inv = make_user(db, "investigador")
    ev_user = make_user(db, "evaluador")
    exp = Expediente(codigo_unico="EXP-1", titulo_protocolo="T", investigador_id=inv.id)
    db.add(exp)
    db.commit()
    db.refresh(exp)

    ev = Evaluacion(expediente_id=exp.id, evaluador_id=ev_user.id)
    ev.criterios.append(EvaluacionCriterio(criterio_key="principios_eticos", puntaje=4, observacion="ok"))
    ev.puntaje_total = 4
    ev.resultado = "no_aprobado"
    db.add(ev)
    db.commit()
    db.refresh(ev)

    assert ev.criterios[0].criterio_key == "principios_eticos"
    assert ev.criterios[0].puntaje == 4
    assert ev.puntaje_total == 4
    assert ev.resultado == "no_aprobado"
```

- [ ] **Step 2: Correr (debe fallar)**

Run: `pytest tests/test_modelo_criterios.py -v`
Expected: FAIL con `ImportError: cannot import name 'EvaluacionCriterio'`.

- [ ] **Step 3: Implementar columnas en `Evaluacion`**

En la clase `Evaluacion` (después de `fecha_envio`, antes de las relationships), agregar:
```python
    puntaje_total = Column(Integer, nullable=True)
    resultado = Column(String(50), nullable=True)
```
Y agregar a las relationships de `Evaluacion`:
```python
    criterios = relationship("EvaluacionCriterio", back_populates="evaluacion", cascade="all, delete-orphan")
```

- [ ] **Step 4: Implementar clase `EvaluacionCriterio`**

Justo después de la clase `Evaluacion` agregar:
```python
class EvaluacionCriterio(Base):
    """Puntaje y observación de un criterio de la rúbrica para una evaluación."""
    __tablename__ = "evaluacion_criterios"

    id = Column(Integer, primary_key=True, index=True)
    evaluacion_id = Column(Integer, ForeignKey("evaluaciones.id"), nullable=False)
    criterio_key = Column(String(50), nullable=False)
    puntaje = Column(Integer, nullable=False, default=0)
    observacion = Column(Text, nullable=True)

    evaluacion = relationship("Evaluacion", back_populates="criterios")
```

- [ ] **Step 5: Correr (debe pasar)**

Run: `pytest tests/test_modelo_criterios.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add app/models/__init__.py tests/test_modelo_criterios.py
git commit -m "feat(eval): tabla evaluacion_criterios + puntaje_total/resultado en Evaluacion"
```

---

### Task 4: Schemas Pydantic de rúbrica y evaluación

**Files:**
- Modify: `app/schemas/__init__.py` (zona de Evaluacion ~líneas 156-184)
- Test: `tests/test_schemas_rubrica.py`

**Interfaces:**
- Produces:
  - `CriterioRubricaItem`: `key, nombre, descripcion, puntaje_max`.
  - `RubricaResponse`: `criterios: List[CriterioRubricaItem]`, `puntaje_total_max: int`, `umbrales: dict`.
  - `CriterioEvaluacionInput`: `key: str, puntaje: int, observacion: Optional[str] = None`.
  - `CriterioEvaluacionResponse`: `criterio_key: str, puntaje: int, observacion: Optional[str]`.
  - `EvaluacionUpdate` extendido con `criterios: Optional[List[CriterioEvaluacionInput]] = None`.
  - `EvaluacionResponse` extendido con `criterios: List[CriterioEvaluacionResponse] = []`, `puntaje_total: Optional[int] = None`, `resultado: Optional[str] = None`.

- [ ] **Step 1: Escribir el test (falla)**

Create `tests/test_schemas_rubrica.py`:
```python
from app.schemas import (
    CriterioRubricaItem, RubricaResponse,
    CriterioEvaluacionInput, EvaluacionUpdate,
)


def test_input_criterios_en_evaluacion_update():
    upd = EvaluacionUpdate(criterios=[
        CriterioEvaluacionInput(key="principios_eticos", puntaje=4, observacion="ok"),
    ], completa=True)
    assert upd.criterios[0].key == "principios_eticos"
    assert upd.completa is True


def test_rubrica_response():
    r = RubricaResponse(
        criterios=[CriterioRubricaItem(key="k", nombre="n", descripcion="d", puntaje_max=2)],
        puntaje_total_max=20,
        umbrales={"aprobado": "17-20"},
    )
    assert r.puntaje_total_max == 20
```

- [ ] **Step 2: Correr (debe fallar)**

Run: `pytest tests/test_schemas_rubrica.py -v`
Expected: FAIL con `ImportError: cannot import name 'CriterioRubricaItem'`.

- [ ] **Step 3: Implementar schemas nuevos**

En `app/schemas/__init__.py`, antes de `class EvaluacionBase`, agregar:
```python
class CriterioRubricaItem(BaseModel):
    key: str
    nombre: str
    descripcion: str
    puntaje_max: int

class RubricaResponse(BaseModel):
    criterios: List[CriterioRubricaItem]
    puntaje_total_max: int
    umbrales: dict

class CriterioEvaluacionInput(BaseModel):
    key: str
    puntaje: int
    observacion: Optional[str] = None

class CriterioEvaluacionResponse(BaseModel):
    criterio_key: str
    puntaje: int
    observacion: Optional[str] = None

    class Config:
        from_attributes = True
```

- [ ] **Step 4: Extender `EvaluacionUpdate`**

Reemplazar `class EvaluacionUpdate(...)` (líneas 162-166) por:
```python
class EvaluacionUpdate(BaseModel):
    nivel_riesgo: Optional[str] = None
    recommendation: Optional[str] = None
    observaciones: Optional[str] = None
    completa: Optional[bool] = None
    criterios: Optional[List[CriterioEvaluacionInput]] = None
```

- [ ] **Step 5: Extender `EvaluacionResponse`**

En `class EvaluacionResponse` agregar antes de `created_at`:
```python
    criterios: List[CriterioEvaluacionResponse] = []
    puntaje_total: Optional[int] = None
    resultado: Optional[str] = None
```

- [ ] **Step 6: Correr (debe pasar)**

Run: `pytest tests/test_schemas_rubrica.py -v`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add app/schemas/__init__.py tests/test_schemas_rubrica.py
git commit -m "feat(eval): schemas de rúbrica e input/response de criterios"
```

---

### Task 5: Endpoint `GET /evaluacion/rubrica`

**Files:**
- Modify: `app/api/evaluacion/routes.py`
- Test: `tests/test_endpoint_rubrica.py`

**Interfaces:**
- Consumes: `CRITERIOS_RUBRICA`, `PUNTAJE_TOTAL_MAX`, `RubricaResponse`.
- Produces: `GET /api/v1/evaluacion/rubrica` → `RubricaResponse`.

**Nota:** definir la ruta `/rubrica` ANTES de `/{evaluacion_id}` para que no la capture la ruta dinámica.

- [ ] **Step 1: Escribir el test (falla)**

Create `tests/test_endpoint_rubrica.py`:
```python
from tests.conftest import make_user, auth_as
from app.api.auth.routes import get_current_user
from app.main import app


def test_get_rubrica(client, db):
    user = make_user(db, "evaluador")
    app.dependency_overrides[get_current_user] = auth_as(user)
    resp = client.get("/api/v1/evaluacion/rubrica")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["criterios"]) == 7
    assert data["puntaje_total_max"] == 20
    assert "aprobado" in data["umbrales"]
```

- [ ] **Step 2: Correr (debe fallar)**

Run: `pytest tests/test_endpoint_rubrica.py -v`
Expected: FAIL (404 o validación), la ruta no existe.

- [ ] **Step 3: Implementar endpoint**

En `app/api/evaluacion/routes.py`, actualizar imports:
```python
from app.models import User, RolEnum, Expediente, Evaluacion, EvaluacionCriterio, EstadoExpedienteEnum, Notificacion, CRITERIOS_RUBRICA, PUNTAJE_TOTAL_MAX, CRITERIOS_MAX_POR_KEY, resultado_por_puntaje
from app.schemas import EvaluacionCreate, EvaluacionResponse, EvaluacionUpdate, EvaluacionAsignarRequest, RubricaResponse, CriterioRubricaItem
```
Y agregar la ruta justo después de `router = APIRouter()` (antes de cualquier ruta `/{evaluacion_id}`):
```python
@router.get("/rubrica", response_model=RubricaResponse)
def get_rubrica(current_user: User = Depends(get_current_user)):
    return RubricaResponse(
        criterios=[CriterioRubricaItem(**c) for c in CRITERIOS_RUBRICA],
        puntaje_total_max=PUNTAJE_TOTAL_MAX,
        umbrales={"aprobado": "17-20", "aprobado_observaciones": "13-16", "no_aprobado": "0-12"},
    )
```

- [ ] **Step 4: Correr (debe pasar)**

Run: `pytest tests/test_endpoint_rubrica.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/api/evaluacion/routes.py tests/test_endpoint_rubrica.py
git commit -m "feat(eval): endpoint GET /evaluacion/rubrica"
```

---

### Task 6: `PUT /evaluacion/{id}` — guardar criterios y cálculo automático al completar

**Files:**
- Modify: `app/api/evaluacion/routes.py` (función `update_evaluacion`, líneas 50-70)
- Test: `tests/test_completar_evaluacion.py`

**Interfaces:**
- Consumes: `EvaluacionUpdate.criterios`, `CRITERIOS_MAX_POR_KEY`, `resultado_por_puntaje`, `EvaluacionCriterio`.
- Produces: al `PUT` con `completa=True` y criterios válidos: guarda criterios, calcula `puntaje_total`, `resultado`, y setea `Expediente.estado` = resultado. Devuelve `EvaluacionResponse` con criterios/total/resultado.

**Reglas de validación (al completar):**
- Deben venir los 7 criterios (todas las keys de `CRITERIOS_MAX_POR_KEY`). Falta alguna → `400` "Faltan criterios por evaluar".
- Cada `puntaje` en `0..CRITERIOS_MAX_POR_KEY[key]`. Fuera de rango → `400` con el criterio.
- Key desconocida → `400`.

- [ ] **Step 1: Escribir los tests (fallan)**

Create `tests/test_completar_evaluacion.py`:
```python
import pytest
from tests.conftest import make_user, auth_as
from app.api.auth.routes import get_current_user
from app.main import app
from app.models import Expediente, Evaluacion


def _setup(db):
    inv = make_user(db, "investigador")
    ev_user = make_user(db, "evaluador")
    exp = Expediente(codigo_unico="EXP-1", titulo_protocolo="T", investigador_id=inv.id, estado="en_revision")
    db.add(exp); db.commit(); db.refresh(exp)
    ev = Evaluacion(expediente_id=exp.id, evaluador_id=ev_user.id)
    db.add(ev); db.commit(); db.refresh(ev)
    app.dependency_overrides[get_current_user] = auth_as(ev_user)
    return exp, ev


def _criterios(p_pobl=2):
    return [
        {"key": "valor_pertinencia", "puntaje": 2, "observacion": None},
        {"key": "principios_eticos", "puntaje": 4, "observacion": None},
        {"key": "consentimiento_informado", "puntaje": 4, "observacion": None},
        {"key": "proteccion_participantes", "puntaje": 3, "observacion": None},
        {"key": "poblaciones_vulnerables", "puntaje": p_pobl, "observacion": None},
        {"key": "confidencialidad_datos", "puntaje": 3, "observacion": None},
        {"key": "adecuacion_metodologica", "puntaje": 2, "observacion": None},
    ]


def test_completar_aprobado_setea_estado(client, db):
    exp, ev = _setup(db)
    resp = client.put(f"/api/v1/evaluacion/{ev.id}", json={"completa": True, "criterios": _criterios()})
    assert resp.status_code == 200
    data = resp.json()
    assert data["puntaje_total"] == 20
    assert data["resultado"] == "aprobado"
    db.refresh(exp)
    assert exp.estado == "aprobado"


def test_completar_con_observaciones(client, db):
    exp, ev = _setup(db)
    crit = _criterios()
    crit[1]["puntaje"] = 1  # principios_eticos 4->1  => total 17-3 = 17? recalc: 2+1+4+3+2+3+2=17 -> aprobado
    crit[2]["puntaje"] = 0  # consentimiento 4->0 => total 13 -> aprobado_observaciones
    resp = client.put(f"/api/v1/evaluacion/{ev.id}", json={"completa": True, "criterios": crit})
    assert resp.json()["puntaje_total"] == 13
    assert resp.json()["resultado"] == "aprobado_observaciones"


def test_completar_no_aprobado(client, db):
    exp, ev = _setup(db)
    crit = _criterios(p_pobl=0)
    crit[1]["puntaje"] = 0
    crit[2]["puntaje"] = 0
    # total = 2+0+0+3+0+3+2 = 10
    resp = client.put(f"/api/v1/evaluacion/{ev.id}", json={"completa": True, "criterios": crit})
    assert resp.json()["puntaje_total"] == 10
    assert resp.json()["resultado"] == "no_aprobado"
    db.refresh(exp)
    assert exp.estado == "no_aprobado"


def test_puntaje_fuera_de_rango(client, db):
    exp, ev = _setup(db)
    crit = _criterios()
    crit[0]["puntaje"] = 5  # max 2
    resp = client.put(f"/api/v1/evaluacion/{ev.id}", json={"completa": True, "criterios": crit})
    assert resp.status_code == 400


def test_faltan_criterios(client, db):
    exp, ev = _setup(db)
    resp = client.put(f"/api/v1/evaluacion/{ev.id}", json={"completa": True, "criterios": _criterios()[:3]})
    assert resp.status_code == 400
```

- [ ] **Step 2: Correr (deben fallar)**

Run: `pytest tests/test_completar_evaluacion.py -v`
Expected: FAIL (no guarda criterios ni calcula; estado no cambia).

- [ ] **Step 3: Implementar la lógica en `update_evaluacion`**

Reemplazar el cuerpo de `update_evaluacion` (líneas 50-70) por:
```python
@router.put("/{evaluacion_id}", response_model=EvaluacionResponse)
def update_evaluacion(evaluacion_id: int, eval_update: EvaluacionUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    evaluacion = db.query(Evaluacion).options(joinedload(Evaluacion.expediente)).filter(Evaluacion.id == evaluacion_id).first()
    if not evaluacion:
        raise HTTPException(status_code=404, detail="Evaluación no encontrada")
    if evaluacion.evaluador_id != current_user.id and current_user.rol != RolEnum.ADMINISTRADOR:
        raise HTTPException(status_code=403, detail="No puedes modificar esta evaluación")

    if eval_update.nivel_riesgo is not None:
        evaluacion.nivel_riesgo = eval_update.nivel_riesgo
    if eval_update.recommendation is not None:
        evaluacion.recommendation = eval_update.recommendation
    if eval_update.observaciones is not None:
        evaluacion.observaciones = eval_update.observaciones

    # Upsert de criterios (reemplaza los existentes por los enviados)
    if eval_update.criterios is not None:
        for c in eval_update.criterios:
            if c.key not in CRITERIOS_MAX_POR_KEY:
                raise HTTPException(status_code=400, detail=f"Criterio desconocido: {c.key}")
            maximo = CRITERIOS_MAX_POR_KEY[c.key]
            if c.puntaje < 0 or c.puntaje > maximo:
                raise HTTPException(status_code=400, detail=f"Puntaje de '{c.key}' debe estar entre 0 y {maximo}")
        # borrar previos y recrear
        evaluacion.criterios.clear()
        for c in eval_update.criterios:
            evaluacion.criterios.append(EvaluacionCriterio(criterio_key=c.key, puntaje=c.puntaje, observacion=c.observacion))

    if eval_update.completa is not None:
        evaluacion.completa = eval_update.completa
        if eval_update.completa:
            # Validar que estén los 7 criterios
            keys_presentes = {c.criterio_key for c in evaluacion.criterios}
            if keys_presentes != set(CRITERIOS_MAX_POR_KEY.keys()):
                raise HTTPException(status_code=400, detail="Faltan criterios por evaluar (se requieren los 7)")
            total = sum(c.puntaje for c in evaluacion.criterios)
            evaluacion.puntaje_total = total
            evaluacion.resultado = resultado_por_puntaje(total)
            evaluacion.fecha_envio = datetime.utcnow()
            if evaluacion.expediente:
                evaluacion.expediente.estado = evaluacion.resultado

    db.commit()
    db.refresh(evaluacion)
    db.refresh(evaluacion, attribute_names=['expediente', 'criterios'])
    return evaluacion
```

- [ ] **Step 4: Correr (deben pasar)**

Run: `pytest tests/test_completar_evaluacion.py -v`
Expected: PASS (5 tests).

- [ ] **Step 5: Correr toda la suite**

Run: `pytest -v`
Expected: todos PASS.

- [ ] **Step 6: Commit**

```bash
git add app/api/evaluacion/routes.py tests/test_completar_evaluacion.py
git commit -m "feat(eval): guardar criterios y calcular resultado/estado al completar evaluación"
```

---

### Task 7: Dictamen automático (sin mínimo de 2, deriva del resultado, PDF para 3 estados)

**Files:**
- Modify: `app/api/dictamen/routes.py`
- Test: `tests/test_dictamen_automatico.py`

**Interfaces:**
- Consumes: `Evaluacion.resultado` (de Task 6).
- Produces: `POST /api/v1/dictamen/` deriva `tipo_dictamen` del resultado de la única evaluación completa (ignora cualquier query param). Requiere 1 evaluación completa con `resultado`. `firmar` genera PDF para los 3 tipos.

- [ ] **Step 1: Escribir tests (fallan)**

Create `tests/test_dictamen_automatico.py`:
```python
from tests.conftest import make_user, auth_as
from app.api.auth.routes import get_current_user
from app.main import app
from app.models import Expediente, Evaluacion


def test_dictamen_deriva_resultado_con_una_evaluacion(client, db):
    inv = make_user(db, "investigador")
    coord = make_user(db, "coordinador")
    exp = Expediente(codigo_unico="EXP-1", titulo_protocolo="T", investigador_id=inv.id)
    db.add(exp); db.commit(); db.refresh(exp)
    ev = Evaluacion(expediente_id=exp.id, evaluador_id=inv.id, completa=True,
                    puntaje_total=14, resultado="aprobado_observaciones")
    db.add(ev); db.commit()
    app.dependency_overrides[get_current_user] = auth_as(coord)

    resp = client.post("/api/v1/dictamen/", json={"expediente_id": exp.id, "contenido": "x"})
    assert resp.status_code == 200
    assert resp.json()["tipo_dictamen"] == "aprobado_observaciones"


def test_dictamen_sin_evaluacion_completa_falla(client, db):
    inv = make_user(db, "investigador")
    coord = make_user(db, "coordinador")
    exp = Expediente(codigo_unico="EXP-2", titulo_protocolo="T", investigador_id=inv.id)
    db.add(exp); db.commit(); db.refresh(exp)
    app.dependency_overrides[get_current_user] = auth_as(coord)
    resp = client.post("/api/v1/dictamen/", json={"expediente_id": exp.id, "contenido": "x"})
    assert resp.status_code == 400
```

- [ ] **Step 2: Correr (fallan)**

Run: `pytest tests/test_dictamen_automatico.py -v`
Expected: FAIL (hoy exige 2 evaluaciones y tipo por query param).

- [ ] **Step 3: Implementar — `TIPOS_DICTAMEN_VALIDOS` y `create_dictamen`**

En `app/api/dictamen/routes.py`:
- Cambiar línea 17 por:
```python
TIPOS_DICTAMEN_VALIDOS = ["aprobado", "aprobado_observaciones", "no_aprobado"]
```
- Reemplazar la firma y cuerpo de `create_dictamen` (líneas 45-92) por:
```python
@router.post("/", response_model=DictamenResponse)
def create_dictamen(
    dictamen: DictamenCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Crea un dictamen derivando el tipo del resultado de la evaluación.

    **Validaciones:**
    - Solo coordinadores/administradores.
    - Requiere 1 evaluación completa con resultado.
    - tipo_dictamen se deriva del resultado (no se pasa manual).
    """
    if current_user.rol not in [RolEnum.ADMINISTRADOR, RolEnum.COORDINADOR]:
        raise HTTPException(status_code=403, detail="Solo coordinadores pueden generar dictámenes")

    exp = db.query(Expediente).filter(Expediente.id == dictamen.expediente_id).first()
    if not exp:
        raise HTTPException(status_code=404, detail="Expediente no encontrado")

    evaluacion = db.query(Evaluacion).filter(
        Evaluacion.expediente_id == dictamen.expediente_id,
        Evaluacion.completa == True,
        Evaluacion.resultado != None,
    ).first()

    if not evaluacion:
        raise HTTPException(status_code=400, detail="Se necesita una evaluación completa con resultado para generar el dictamen")

    tipo = evaluacion.resultado
    if tipo not in TIPOS_DICTAMEN_VALIDOS:
        raise HTTPException(status_code=400, detail=f"Resultado de evaluación inválido: {tipo}")

    nuevo_dictamen = Dictamen(
        expediente_id=dictamen.expediente_id,
        contenido=dictamen.contenido,
        tipo_dictamen=tipo,
        numero_dictamen=generar_numero_dictamen(),
        fecha_emision=datetime.utcnow()
    )
    db.add(nuevo_dictamen)
    db.commit()
    db.refresh(nuevo_dictamen)
    return nuevo_dictamen
```

- [ ] **Step 4: Implementar — PDF para los 3 estados en `firmar_dictamen`**

En `firmar_dictamen`, reemplazar el bloque `if dictamen.tipo_dictamen and ... == "aprobado":` ... `else:` (líneas 144-176) por una generación de PDF incondicional:
```python
    try:
        exp = db.query(Expediente).filter(Expediente.id == dictamen.expediente_id).first()
        if not exp:
            raise HTTPException(status_code=404, detail="Expediente no encontrado")
        investigador = db.query(User).filter(User.id == exp.investigador_id).first()
        nombres_investigadores = f"{investigador.nombre} {investigador.apellido}" if investigador else "No especificado"
        fecha_firma = datetime.utcnow()
        pdf_path = generar_pdf_dictamen(
            numero_dictamen=dictamen.numero_dictamen or "DICT-SIN-NUMERO",
            titulo=exp.titulo_protocolo,
            contenido=dictamen.contenido,
            investigador_nombre=nombres_investigadores,
            dictamen_fecha=fecha_firma
        )
        dictamen.archivo_url = pdf_path
        dictamen.fecha_firma = fecha_firma
        dictamen.firmado = True
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generando PDF: {str(e)}")
```

- [ ] **Step 5: Correr (pasan)**

Run: `pytest tests/test_dictamen_automatico.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add app/api/dictamen/routes.py tests/test_dictamen_automatico.py
git commit -m "feat(dictamen): derivar tipo del resultado, sin mínimo de 2, PDF para 3 estados"
```

---

### Task 8: Reportes — incluir los 3 estados

**Files:**
- Modify: `app/api/reportes/routes.py` (función `reportes_resultados`, líneas 64-88)
- Test: `tests/test_reportes_resultados.py`

**Interfaces:**
- Consumes: `Dictamen.tipo_dictamen` con valores de los 3 estados.
- Produces: `GET /api/v1/reportes/resultados-emitidos` cuenta los 3 tipos (incluido `no_aprobado`).

- [ ] **Step 1: Escribir el test (falla)**

Create `tests/test_reportes_resultados.py`:
```python
from tests.conftest import make_user, auth_as
from app.api.auth.routes import get_current_user
from app.main import app
from app.models import Dictamen


def test_resultados_incluye_no_aprobado(client, db):
    coord = make_user(db, "coordinador")
    db.add(Dictamen(expediente_id=1, contenido="x", tipo_dictamen="no_aprobado", numero_dictamen="D1"))
    db.add(Dictamen(expediente_id=2, contenido="x", tipo_dictamen="aprobado", numero_dictamen="D2"))
    db.commit()
    app.dependency_overrides[get_current_user] = auth_as(coord)
    resp = client.get("/api/v1/reportes/resultados-emitidos")
    assert resp.status_code == 200
    tipos = {r["tipo"] for r in resp.json()}
    assert "no_aprobado" in tipos
    assert "aprobado" in tipos
```

- [ ] **Step 2: Correr (falla)**

Run: `pytest tests/test_reportes_resultados.py -v`
Expected: FAIL (hoy filtra a `["aprobado", "observado"]`).

- [ ] **Step 3: Implementar**

En `reportes_resultados` reemplazar el cuerpo (líneas 71-88) por:
```python
    TIPOS_VALIDOS = ["aprobado", "aprobado_observaciones", "no_aprobado"]
    resultados = db.query(
        Dictamen.tipo_dictamen,
        func.count(Dictamen.id).label("total")
    ).filter(
        Dictamen.tipo_dictamen.in_(TIPOS_VALIDOS)
    ).group_by(Dictamen.tipo_dictamen).all()

    datos = []
    for r in resultados:
        tipo = r[0] if r[0] else "sin tipo"
        if tipo.lower() not in TIPOS_VALIDOS:
            continue
        datos.append(ReporteResultados(tipo=tipo, total=r[1]))
    return datos
```
Y actualizar el docstring de la función (línea 69) a: `**Retorna:** aprobado, aprobado_observaciones, no_aprobado`.

- [ ] **Step 4: Correr (pasa) + suite completa**

Run: `pytest -v`
Expected: todos PASS.

- [ ] **Step 5: Commit**

```bash
git add app/api/reportes/routes.py tests/test_reportes_resultados.py
git commit -m "feat(reportes): incluir los 3 estados de dictamen en resultados-emitidos"
```

---

### Task 9: Migración manual en Aiven (columnas nuevas) — documentar y ejecutar

**Files:**
- Create: `docs/migraciones/2026-06-29-rubrica.sql`

**Contexto:** `create_all` crea la tabla nueva `evaluacion_criterios` pero NO agrega columnas a `evaluaciones` existentes en Aiven. Hay que correr el `ALTER TABLE` manual.

- [ ] **Step 1: Escribir el SQL de migración**

Create `docs/migraciones/2026-06-29-rubrica.sql`:
```sql
-- Columnas nuevas en evaluaciones (idempotente en PostgreSQL 9.6+)
ALTER TABLE evaluaciones ADD COLUMN IF NOT EXISTS puntaje_total INTEGER;
ALTER TABLE evaluaciones ADD COLUMN IF NOT EXISTS resultado VARCHAR(50);

-- La tabla evaluacion_criterios la crea create_all; si se requiere manual:
CREATE TABLE IF NOT EXISTS evaluacion_criterios (
    id SERIAL PRIMARY KEY,
    evaluacion_id INTEGER NOT NULL REFERENCES evaluaciones(id),
    criterio_key VARCHAR(50) NOT NULL,
    puntaje INTEGER NOT NULL DEFAULT 0,
    observacion TEXT
);
```

- [ ] **Step 2: Ejecutar contra Aiven (manual, requiere DATABASE_URL de Aiven)**

Run (con la URI de Aiven en `backend/.env`):
`python -c "from app.db.database import engine; from sqlalchemy import text; [engine.connect().execute(text(s)) for s in open('docs/migraciones/2026-06-29-rubrica.sql').read().split(';') if s.strip()]"`
Expected: sin error. (Alternativa: ejecutar el `.sql` con un cliente PostgreSQL.)
**Nota:** este paso lo confirma el usuario en su entorno; no se corre en CI/tests.

- [ ] **Step 3: Commit**

```bash
git add docs/migraciones/2026-06-29-rubrica.sql
git commit -m "chore(db): SQL de migración manual para rúbrica en Aiven"
```

---

## Self-Review

**Spec coverage:**
- Catálogo 7 criterios + suma 20 → Task 1 ✓
- Umbrales / resultado automático → Task 1 (función) + Task 6 (aplicación) ✓
- Enums 3 estados (expediente + dictamen) → Task 2 ✓
- Tabla `evaluacion_criterios` + columnas → Task 3 ✓
- Schemas (rúbrica + input/response) → Task 4 ✓
- `GET /evaluacion/rubrica` → Task 5 ✓
- `PUT /evaluacion/{id}` con criterios + set estado → Task 6 ✓
- 1 evaluador (sin mínimo de 2) + dictamen automático + PDF 3 estados → Task 7 ✓
- Reportes incluye no_aprobado → Task 8 ✓
- Migración manual Aiven (nota de despliegue del spec) → Task 9 ✓
- "Poblaciones vulnerables = 0 si no aplica" → modelado como criterio normal 0-2 (sin N/A), cubierto en Task 1/6 ✓

**Fuera de este plan (frontend, plan 2):** formulario de rúbrica del evaluador, `status-badge`/`types`, servicios de evaluación/dictamen, ajuste de la vista de consolidación.

**Pendiente conocido:** `create_evaluacion` y `asignar_evaluador_manual` aún permiten hasta 2 evaluaciones. Con el modelo de 1 evaluador convendría bajar el tope a 1; se aborda en el plan de frontend/limpieza o como tarea menor de seguimiento (no bloquea el cálculo automático).

**Type consistency:** strings de resultado/estado/dictamen idénticos en todas las tareas (`aprobado`/`aprobado_observaciones`/`no_aprobado`); `CRITERIOS_MAX_POR_KEY` usado en Tasks 5/6; `resultado_por_puntaje` definido en Task 1 y usado en Task 6.
