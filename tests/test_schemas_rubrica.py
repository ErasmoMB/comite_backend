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
