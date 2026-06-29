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
