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
