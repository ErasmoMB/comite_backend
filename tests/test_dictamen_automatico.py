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
