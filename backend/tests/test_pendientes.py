"""Pruebas mínimas de los handlers que cada integrante va a implementar.
Al implementar su flujo, reemplacen estas pruebas por las reales."""
import json

from conftest import api_event
from paseqr.handlers import checkin, compras, generar_boleto, recordatorios


def test_compras_pendiente():
    assert compras.handler(api_event("POST /compras", {}), None)["statusCode"] == 501


def test_checkin_pendiente():
    assert checkin.handler(api_event("POST /checkin", {}), None)["statusCode"] == 501


def test_generar_boleto_no_reporta_fallos():
    evento = {"Records": [{"messageId": "1", "body": json.dumps({"boleto_id": "b1"})}]}
    assert generar_boleto.handler(evento, None) == {"batchItemFailures": []}


def test_recordatorios_corre():
    assert recordatorios.handler({"time": "2026-10-08T12:00:00Z"}, None)["reportes"] == 0
