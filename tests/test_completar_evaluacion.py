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
    crit[1]["puntaje"] = 1
    crit[2]["puntaje"] = 0
    # total = 2+1+0+3+2+3+2 = 13 -> aprobado_observaciones
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
