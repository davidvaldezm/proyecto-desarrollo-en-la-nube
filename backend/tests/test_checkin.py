import json
import uuid

import pytest

from conftest import api_event, crear_evento, procesar_cola
from paseqr.common import qr
from paseqr.handlers import checkin, compras


@pytest.fixture
def boleto(aws):
    """Evento con un boleto ya emitido. Devuelve (evento_id, contenido del QR)."""
    ev = crear_evento(pin="2468")
    body = {"compra_id": str(uuid.uuid4()), "evento_id": ev["evento_id"], "nombre": "Ana",
            "email": "ana@iteso.mx", "cantidad": 1}
    boleto_id = json.loads(compras.handler(api_event("POST /compras", body), None)["body"])["boletos"][0]["boleto_id"]
    procesar_cola()
    return ev["evento_id"], qr.firmar(boleto_id, ev["evento_id"])


def escanear(evento_id, codigo, pin="2468"):
    resp = checkin.handler(api_event("POST /checkin", {"evento_id": evento_id, "pin_staff": pin, "qr": codigo}), None)
    return resp["statusCode"], json.loads(resp["body"])


def test_qr_valido_y_luego_ya_usado(boleto):
    evento_id, codigo = boleto
    status, r = escanear(evento_id, codigo)
    assert status == 200 and r["resultado"] == "VALIDO" and r["asistentes"] == 1 and r["nombre"] == "Ana"
    _, r2 = escanear(evento_id, codigo)
    assert r2["resultado"] == "YA_USADO" and r2["usado_en"] == r["usado_en"]


def test_qr_alterado_es_invalido(boleto):
    evento_id, codigo = boleto
    alterado = codigo[:-1] + ("A" if codigo[-1] != "A" else "B")
    assert escanear(evento_id, alterado)[1]["resultado"] == "INVALIDO"
    assert escanear(evento_id, "cualquier-cosa-123")[1]["resultado"] == "INVALIDO"


def test_qr_forjado_sin_llave_es_invalido(boleto):
    evento_id, codigo = boleto
    _, boleto_id, ev, _ = codigo.split(".")
    assert escanear(evento_id, f"v1.{boleto_id}.{ev}.firmaInventada")[1]["resultado"] == "INVALIDO"


def test_qr_de_otro_evento(boleto):
    evento_id, codigo = boleto
    otro = crear_evento(pin="2468")
    assert escanear(otro["evento_id"], codigo)[1]["resultado"] == "OTRO_EVENTO"


def test_pin_incorrecto(boleto):
    evento_id, codigo = boleto
    assert escanear(evento_id, codigo, pin="0000")[0] == 403


def test_tercer_escaneo_sigue_rechazado_y_cuenta_una_vez(boleto):
    evento_id, codigo = boleto
    resultados = [escanear(evento_id, codigo)[1] for _ in range(3)]
    assert [r["resultado"] for r in resultados] == ["VALIDO", "YA_USADO", "YA_USADO"]
    assert resultados[-1]["asistentes"] == 1


def test_firma_round_trip(aws):
    codigo = qr.firmar("abc#1", "ev-1")
    assert qr.verificar(codigo) == ("abc#1", "ev-1")
    with pytest.raises(qr.QRInvalido):
        qr.verificar(codigo.replace("ev-1", "ev-2"))
