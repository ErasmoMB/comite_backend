from tests.conftest import make_user, auth_as
from app.api.auth.routes import get_current_user
from app.main import app


def _como(user):
    app.dependency_overrides[get_current_user] = auth_as(user)


# ---------- Lado solicitante ----------

def test_solicitante_envia_y_lee_su_hilo(client, db):
    est = make_user(db, "estudiante_pregrado")
    _como(est)

    r = client.post("/api/v1/chat/mios", json={"texto": "Hola, ¿qué documentos necesito?"})
    assert r.status_code == 200
    assert r.json()["texto"] == "Hola, ¿qué documentos necesito?"
    assert r.json()["es_de_secretaria"] is False

    r = client.get("/api/v1/chat/mios")
    assert r.status_code == 200
    mensajes = r.json()
    assert len(mensajes) == 1
    assert mensajes[0]["autor_id"] == est.id


def test_rol_interno_no_usa_endpoints_de_solicitante(client, db):
    ev = make_user(db, "evaluador")
    _como(ev)
    assert client.get("/api/v1/chat/mios").status_code == 403
    assert client.post("/api/v1/chat/mios", json={"texto": "x"}).status_code == 403


def test_texto_vacio_o_muy_largo_da_400(client, db):
    est = make_user(db, "estudiante_pregrado")
    _como(est)
    assert client.post("/api/v1/chat/mios", json={"texto": "   "}).status_code == 400
    assert client.post("/api/v1/chat/mios", json={"texto": "x" * 2001}).status_code == 400


def test_no_leidos_del_solicitante(client, db):
    est = make_user(db, "estudiante_pregrado")
    sec = make_user(db, "secretaria")

    _como(sec)
    client.post(f"/api/v1/chat/{est.id}", json={"texto": "Le falta la boleta"})

    _como(est)
    r = client.get("/api/v1/chat/mios/no-leidos")
    assert r.status_code == 200
    assert r.json()["no_leidos"] == 1

    # Abrir el hilo marca como leído
    client.get("/api/v1/chat/mios")
    assert client.get("/api/v1/chat/mios/no-leidos").json()["no_leidos"] == 0


# ---------- Lado secretaría ----------

def test_solicitante_no_usa_endpoints_de_secretaria(client, db):
    est = make_user(db, "estudiante_pregrado")
    otro = make_user(db, "investigador")
    _como(est)
    assert client.get("/api/v1/chat/conversaciones").status_code == 403
    assert client.get("/api/v1/chat/solicitantes").status_code == 403
    assert client.get(f"/api/v1/chat/{otro.id}").status_code == 403
    assert client.post(f"/api/v1/chat/{otro.id}", json={"texto": "x"}).status_code == 403


def test_bandeja_agrupada_con_datos_y_no_leidos(client, db):
    est = make_user(db, "estudiante_pregrado", email="a@test.com")
    est.codigo_estudiante = "2021001"
    inv = make_user(db, "investigador", email="b@test.com")
    sec = make_user(db, "secretaria")
    db.commit()

    _como(est)
    client.post("/api/v1/chat/mios", json={"texto": "Duda 1"})
    client.post("/api/v1/chat/mios", json={"texto": "Duda 2"})
    _como(inv)
    client.post("/api/v1/chat/mios", json={"texto": "Consulta del investigador"})

    _como(sec)
    r = client.get("/api/v1/chat/conversaciones")
    assert r.status_code == 200
    convs = r.json()
    assert len(convs) == 2
    # Ordenada por más reciente: el investigador escribió último
    assert convs[0]["solicitante_id"] == inv.id
    assert convs[0]["codigo_estudiante"] is None
    assert convs[0]["ultimo_mensaje"] == "Consulta del investigador"
    por_id = {c["solicitante_id"]: c for c in convs}
    assert por_id[est.id]["codigo_estudiante"] == "2021001"
    assert por_id[est.id]["no_leidos"] == 2
    assert por_id[est.id]["nombre"] == "Test estudiante_pregrado"

    # Total para el badge
    assert client.get("/api/v1/chat/no-leidos").json()["no_leidos"] == 3


def test_secretaria_lee_hilo_y_marca_leidos(client, db):
    est = make_user(db, "estudiante_pregrado")
    sec = make_user(db, "secretaria")

    _como(est)
    client.post("/api/v1/chat/mios", json={"texto": "Hola"})

    _como(sec)
    r = client.get(f"/api/v1/chat/{est.id}")
    assert r.status_code == 200
    assert len(r.json()) == 1
    # Tras abrir el hilo ya no hay no-leídos
    assert client.get("/api/v1/chat/no-leidos").json()["no_leidos"] == 0


def test_secretaria_inicia_conversacion(client, db):
    inv = make_user(db, "investigador")
    sec = make_user(db, "secretaria")

    _como(sec)
    r = client.post(f"/api/v1/chat/{inv.id}", json={"texto": "Su proyecto tiene una observación"})
    assert r.status_code == 200
    assert r.json()["es_de_secretaria"] is True

    _como(inv)
    mensajes = client.get("/api/v1/chat/mios").json()
    assert len(mensajes) == 1
    assert mensajes[0]["es_de_secretaria"] is True


def test_hilo_de_no_solicitante_da_404(client, db):
    sec = make_user(db, "secretaria")
    coord = make_user(db, "coordinador")
    _como(sec)
    assert client.get("/api/v1/chat/99999").status_code == 404
    assert client.post(f"/api/v1/chat/{coord.id}", json={"texto": "x"}).status_code == 404


def test_lista_de_solicitantes(client, db):
    est = make_user(db, "estudiante_pregrado", email="a@test.com")
    est.codigo_estudiante = "2021001"
    make_user(db, "investigador", email="b@test.com")
    make_user(db, "evaluador", email="c@test.com")
    sec = make_user(db, "secretaria")
    db.commit()

    _como(sec)
    r = client.get("/api/v1/chat/solicitantes")
    assert r.status_code == 200
    roles = {s["rol"] for s in r.json()}
    assert roles == {"estudiante_pregrado", "investigador"}
    por_rol = {s["rol"]: s for s in r.json()}
    assert por_rol["estudiante_pregrado"]["codigo_estudiante"] == "2021001"
