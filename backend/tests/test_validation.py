from datetime import datetime, timezone
from decimal import Decimal

import pytest

from paseqr.common.http import ApiError
from paseqr.common.validation import Validador

AHORA = datetime(2026, 10, 8, tzinfo=timezone.utc)


def test_datos_validos_se_normalizan():
    datos = (
        Validador({"n": "  Hola  ", "e": "A@B.COM", "c": 3, "p": "99.999", "f": "2026-12-01T10:00:00Z"})
        .texto("n").email("e").entero("c", 1, 4).dinero("p").fecha_futura("f", ahora=AHORA)
        .resultado()
    )
    assert datos == {"n": "Hola", "e": "a@b.com", "c": 3, "p": Decimal("100.00"),
                     "f": "2026-12-01T10:00:00+00:00"}


@pytest.mark.parametrize("valor", [True, "3", 3.5, None])
def test_entero_rechaza_tipos_incorrectos(valor):
    with pytest.raises(ApiError) as err:
        Validador({"c": valor}).entero("c", 1, 4).resultado()
    assert "c" in err.value.detalles


def test_fecha_sin_zona_horaria():
    with pytest.raises(ApiError) as err:
        Validador({"f": "2026-12-01T10:00:00"}).fecha_futura("f", ahora=AHORA).resultado()
    assert "zona horaria" in err.value.detalles["f"]


def test_texto_opcional_ausente_no_falla():
    assert Validador({}).texto("d", requerido=False).resultado() == {}
