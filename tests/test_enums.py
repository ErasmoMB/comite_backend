from app.models import EstadoExpedienteEnum, TipoDictamenEnum


def test_estados_nuevos():
    assert EstadoExpedienteEnum.APROBADO.value == "aprobado"
    assert EstadoExpedienteEnum.APROBADO_OBSERVACIONES.value == "aprobado_observaciones"
    assert EstadoExpedienteEnum.NO_APROBADO.value == "no_aprobado"


def test_tipos_dictamen():
    valores = {t.value for t in TipoDictamenEnum}
    assert valores == {"aprobado", "aprobado_observaciones", "no_aprobado"}
