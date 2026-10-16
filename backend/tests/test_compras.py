import json
import uuid

import boto3

from conftest import api_event, crear_evento, procesar_cola
from paseqr.common import db
from paseqr.handlers import compras


def comprar(evento_id, cantidad=1, compra_id=None, email="ana@iteso.mx"):
    body = {"compra_id": compra_id or str(uuid.uuid4()), "evento_id": evento_id, "nombre": "Ana López",
            "email": email, "cantidad": cantidad}
    resp = compras.handler(api_event("POST /compras", body), None)
    return resp["statusCode"], json.loads(resp["body"])


def vendidos(evento_id):
    return int(db.tabla_eventos().get_item(Key={"evento_id": evento_id})["Item"]["vendidos"])


def test_compra_crea_boletos_pendientes_y_mensajes(aws):
    ev = crear_evento(cupo=10)
    status, body = comprar(ev["evento_id"], cantidad=3)
    assert status == 202
    assert [b["estado"] for b in body["boletos"]] == ["PENDIENTE"] * 3
    assert vendidos(ev["evento_id"]) == 3
    assert procesar_cola() == 3


def test_no_hay_sobreventa(aws):
    ev = crear_evento(cupo=2)
    assert comprar(ev["evento_id"])[0] == 202
    assert comprar(ev["evento_id"])[0] == 202
    status, body = comprar(ev["evento_id"])
    assert status == 409
    assert body["detalles"]["disponibles"] == 0
    assert vendidos(ev["evento_id"]) == 2


def test_compra_mayor_al_cupo_restante(aws):
    ev = crear_evento(cupo=3)
    comprar(ev["evento_id"], cantidad=2)
    status, _ = comprar(ev["evento_id"], cantidad=2)
    assert status == 409
    assert vendidos(ev["evento_id"]) == 2


def test_lectura_desactualizada_no_provoca_sobreventa(aws, monkeypatch):
    """Simula la condición de carrera: dos Lambdas leen el evento cuando queda 1 lugar
    y ambas intentan comprar. La condición se evalúa al escribir, así que solo una pasa.
    (moto no es seguro con hilos, por eso se simula el entrelazado en lugar de usar threads;
    en DynamoDB real las escrituras condicionales son atómicas.)"""
    ev = crear_evento(cupo=5)
    comprar(ev["evento_id"], cantidad=4)
    snapshot = db.tabla_eventos().get_item(Key={"evento_id": ev["evento_id"]})["Item"]  # vendidos = 4

    tabla_real = db.tabla_eventos

    class TablaConLecturaVieja:
        def __init__(self):
            self._t = tabla_real()

        def get_item(self, **_kw):
            return {"Item": dict(snapshot)}

        def __getattr__(self, nombre):
            return getattr(self._t, nombre)

    monkeypatch.setattr(db, "tabla_eventos", TablaConLecturaVieja)
    resultados = [comprar(ev["evento_id"])[0] for _ in range(3)]
    assert resultados == [202, 409, 409]
    monkeypatch.setattr(db, "tabla_eventos", tabla_real)
    assert vendidos(ev["evento_id"]) == 5


def test_reintento_misma_compra_no_duplica(aws):
    ev = crear_evento(cupo=10)
    compra_id = str(uuid.uuid4())
    _, primero = comprar(ev["evento_id"], cantidad=2, compra_id=compra_id)
    status, segundo = comprar(ev["evento_id"], cantidad=2, compra_id=compra_id)
    assert status in (200, 202)
    assert [b["boleto_id"] for b in segundo["boletos"]] == [b["boleto_id"] for b in primero["boletos"]]
    assert vendidos(ev["evento_id"]) == 2


def test_validaciones(aws):
    ev = crear_evento()
    body = {"compra_id": "no-uuid", "evento_id": ev["evento_id"], "nombre": "A", "email": "x", "cantidad": 9}
    resp = compras.handler(api_event("POST /compras", body), None)
    assert resp["statusCode"] == 400
    assert set(json.loads(resp["body"])["detalles"]) == {"compra_id", "nombre", "email", "cantidad"}


def test_evento_inexistente(aws):
    assert comprar(str(uuid.uuid4()))[0] == 404


def test_emision_genera_pdf_y_es_idempotente(aws):
    ev = crear_evento()
    _, body = comprar(ev["evento_id"])
    boleto_id = body["boletos"][0]["boleto_id"]
    procesar_cola()
    boleto = db.tabla_boletos().get_item(Key={"boleto_id": boleto_id})["Item"]
    assert boleto["estado"] == "EMITIDO"
    pdf = boto3.client("s3", region_name="us-east-1").get_object(Bucket="test-boletos-bucket", Key=boleto["pdf_key"])
    assert pdf["Body"].read()[:4] == b"%PDF"

    # mensaje duplicado de SQS: no falla ni cambia nada
    from paseqr.handlers import generar_boleto
    dup = {"Records": [{"messageId": "x", "body": json.dumps({"boleto_id": boleto_id})}]}
    assert generar_boleto.handler(dup, None) == {"batchItemFailures": []}
    assert db.tabla_boletos().get_item(Key={"boleto_id": boleto_id})["Item"]["emitido_en"] == boleto["emitido_en"]


def test_mis_boletos_con_url_de_descarga(aws):
    ev = crear_evento()
    comprar(ev["evento_id"], cantidad=2, email="luis@iteso.mx")
    comprar(ev["evento_id"], email="otra@iteso.mx")
    procesar_cola()
    resp = compras.handler({"routeKey": "GET /boletos", "queryStringParameters": {"email": "LUIS@iteso.mx"}}, None)
    boletos = json.loads(resp["body"])["boletos"]
    assert len(boletos) == 2
    assert all(b["estado"] == "EMITIDO" and b["pdf_url"].startswith("https://") for b in boletos)
