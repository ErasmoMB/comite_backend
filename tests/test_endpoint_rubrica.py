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
