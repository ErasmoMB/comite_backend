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
