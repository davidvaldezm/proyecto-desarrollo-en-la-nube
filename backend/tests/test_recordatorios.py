import json
import uuid
from datetime import datetime, timedelta, timezone

import boto3

from conftest import api_event, crear_evento, procesar_cola
from paseqr.common import db, qr
from paseqr.handlers import checkin, compras, recordatorios


def preparar(evento_id, compradores=3, usar=2):
    for i in range(compradores):
        body = {"compra_id": str(uuid.uuid4()), "evento_id": evento_id, "nombre": f"Persona {i}",
                "email": f"p{i}@iteso.mx", "cantidad": 1}
        compras.handler(api_event("POST /compras", body), None)
    procesar_cola()
    boletos = db.tabla_boletos().scan()["Items"]
    for b in boletos[:usar]:
        checkin.handler(api_event("POST /checkin", {"evento_id": evento_id, "pin_staff": "4321",
                                                    "qr": qr.firmar(b["boleto_id"], evento_id)}), None)


def mover_fecha(evento_id, delta):
    nueva = (datetime.now(timezone.utc) + delta).isoformat()
    db.tabla_eventos().update_item(Key={"evento_id": evento_id}, UpdateExpression="SET fecha_inicio = :f",
                                   ExpressionAttributeValues={":f": nueva})


def test_calculo_del_reporte(aws):
    ev = crear_evento(cupo=10)
    preparar(ev["evento_id"], compradores=4, usar=3)
    evento = db.tabla_eventos().get_item(Key={"evento_id": ev["evento_id"]})["Item"]
    resumen, contenido = recordatorios.calcular_reporte(evento, recordatorios._boletos(ev["evento_id"]))
    assert resumen["vendidos"] == 4 and resumen["asistentes"] == 3
    assert resumen["tasa_asistencia"] == "75.0%" and resumen["ingresos"] == "400.00"
    assert resumen["hora_pico"] != "-"
    assert contenido.count("@iteso.mx") == 4


def test_ejecucion_programada_envia_recordatorio_una_vez(aws):
    ev = crear_evento()
    preparar(ev["evento_id"], usar=0)
    mover_fecha(ev["evento_id"], timedelta(hours=20))
    assert recordatorios.handler({}, None) == {"recordatorios": 3, "reportes": 0}
    assert recordatorios.handler({}, None) == {"recordatorios": 0, "reportes": 0}


def test_ejecucion_programada_genera_reporte_de_evento_terminado(aws):
    ev = crear_evento()
    preparar(ev["evento_id"])
    mover_fecha(ev["evento_id"], timedelta(hours=-7))
    assert recordatorios.handler({}, None)["reportes"] == 1
    evento = db.tabla_eventos().get_item(Key={"evento_id": ev["evento_id"]})["Item"]
    assert evento["estado"] == "FINALIZADO"
    csv = boto3.client("s3", region_name="us-east-1").get_object(Bucket="test-boletos-bucket", Key=evento["reporte_key"])
    assert b"asistentes" in csv["Body"].read()
    assert recordatorios.handler({}, None)["reportes"] == 0


def test_invocacion_manual_de_reporte(aws):
    ev = crear_evento()
    preparar(ev["evento_id"])
    r = recordatorios.handler({"accion": "reporte", "evento_id": ev["evento_id"]}, None)
    assert r["vendidos"] == 3 and r["asistentes"] == 2
    assert json.dumps(r)
