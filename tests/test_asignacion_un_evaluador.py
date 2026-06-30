from tests.conftest import make_user, auth_as
from app.api.auth.routes import get_current_user
from app.main import app
from app.models import Expediente


def test_solo_un_evaluador_por_expediente(client, db):
    inv = make_user(db, "investigador")
    coord = make_user(db, "coordinador")
    ev1 = make_user(db, "evaluador", email="ev1@test.com")
    ev2 = make_user(db, "evaluador", email="ev2@test.com")
    exp = Expediente(codigo_unico="EXP-1", titulo_protocolo="T", investigador_id=inv.id)
    db.add(exp); db.commit(); db.refresh(exp)
    app.dependency_overrides[get_current_user] = auth_as(coord)

    # Primer evaluador: OK
    r1 = client.post(f"/api/v1/evaluacion/expediente/{exp.id}/asignar", json={"evaluador_id": ev1.id})
    assert r1.status_code == 200

    # Segundo evaluador: rechazado (solo 1 por expediente)
    r2 = client.post(f"/api/v1/evaluacion/expediente/{exp.id}/asignar", json={"evaluador_id": ev2.id})
    assert r2.status_code == 400
    assert "un evaluador" in r2.json()["detail"]
