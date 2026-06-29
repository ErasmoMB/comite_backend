from tests.conftest import make_user, auth_as
from app.api.auth.routes import get_current_user
from app.main import app
from app.models import Expediente, PROGRAMAS_ESTUDIOS, CICLOS_CAMBIO_TITULO


def _exp(db, user, estado, titulo="Proyecto X", tramite="proyecto_nuevo", codigo="C1"):
    e = Expediente(codigo_unico=codigo, titulo_protocolo=titulo, investigador_id=user.id,
                   estado=estado, tipo_tramite=tramite)
    db.add(e); db.commit(); db.refresh(e)
    return e


def _payload(origen_id, titulo_nuevo="Nuevo titulo del proyecto"):
    return {
        "proyecto_origen_id": origen_id,
        "numero_acta": "ACTA-001",
        "programa_estudios": PROGRAMAS_ESTUDIOS[0],
        "ciclo": CICLOS_CAMBIO_TITULO[0],
        "titulo_nuevo": titulo_nuevo,
        "autores": [{"apellidos_nombres": "Perez Juan", "codigo_estudiante": "123", "correo": "a@b.com"}],
    }


def test_elegibles_solo_aprobados(client, db):
    u = make_user(db, "estudiante_pregrado")
    _exp(db, u, "enviado", titulo="Enviado", codigo="C1")
    _exp(db, u, "aprobado", titulo="Aprobado", codigo="C2")
    _exp(db, u, "aprobado_observaciones", titulo="ConObs", codigo="C3")
    _exp(db, u, "no_aprobado", titulo="Rechazado", codigo="C4")
    app.dependency_overrides[get_current_user] = auth_as(u)

    resp = client.get("/api/v1/expedientes/elegibles-cambio-titulo")
    assert resp.status_code == 200
    titulos = {p["titulo"] for p in resp.json()}
    assert titulos == {"Aprobado", "ConObs"}


def test_cambio_titulo_rechaza_no_aprobado(client, db):
    u = make_user(db, "estudiante_pregrado")
    origen = _exp(db, u, "enviado", codigo="C1")
    app.dependency_overrides[get_current_user] = auth_as(u)
    resp = client.post("/api/v1/expedientes/cambio-titulo", json=_payload(origen.id))
    assert resp.status_code == 400


def test_cambio_titulo_ok_y_autollena_titulo_anterior(client, db):
    u = make_user(db, "estudiante_pregrado")
    origen = _exp(db, u, "aprobado", titulo="Titulo original aprobado", codigo="C1")
    app.dependency_overrides[get_current_user] = auth_as(u)
    resp = client.post("/api/v1/expedientes/cambio-titulo", json=_payload(origen.id))
    assert resp.status_code == 200
    data = resp.json()
    assert data["titulo_anterior"] == "Titulo original aprobado"
    assert data["titulo_nuevo"] == "Nuevo titulo del proyecto"


def test_cambio_titulo_rechaza_proyecto_ajeno(client, db):
    dueno = make_user(db, "estudiante_pregrado", email="dueno@test.com")
    otro = make_user(db, "estudiante_pregrado", email="otro@test.com")
    origen = _exp(db, dueno, "aprobado", codigo="C1")
    app.dependency_overrides[get_current_user] = auth_as(otro)
    resp = client.post("/api/v1/expedientes/cambio-titulo", json=_payload(origen.id))
    assert resp.status_code == 404
