import json

from conftest import api_event
from paseqr.handlers import eventos

EVENTO_OK = {
    "nombre": "Concierto de bienvenida",
    "descripcion": "Bandas del ITESO",
    "lugar": "Auditorio Pedro Arrupe",
    "fecha_inicio": "2099-11-20T20:00:00-06:00",
    "cupo": 150,
    "precio": 120,
    "organizador_email": "Org@Iteso.mx",
    "pin_staff": "4321",
}


def llamar(route, body=None, path=None):
    resp = eventos.handler(api_event(route, body, path), None)
    return resp["statusCode"], json.loads(resp["body"])


def test_crear_evento_valido(aws):
    status, body = llamar("POST /eventos", EVENTO_OK)
    assert status == 201
    assert body["estado"] == "A_LA_VENTA"
    assert body["disponibles"] == 150
    assert body["fecha_inicio"] == "2099-11-21T02:00:00+00:00"  # normalizada a UTC
    assert "pin_staff" not in body and "pin_hash" not in body
    assert "organizador_email" not in body


def test_crear_evento_reporta_todos_los_errores(aws):
    malo = {**EVENTO_OK, "cupo": 0, "organizador_email": "no-es-correo",
            "fecha_inicio": "2000-01-01T00:00:00Z", "pin_staff": "12"}
    status, body = llamar("POST /eventos", malo)
    assert status == 400
    assert set(body["detalles"]) == {"cupo", "organizador_email", "fecha_inicio", "pin_staff"}


def test_crear_evento_sin_cuerpo(aws):
    status, body = llamar("POST /eventos")
    assert status == 400


def test_listar_y_obtener(aws):
    _, creado = llamar("POST /eventos", EVENTO_OK)
    llamar("POST /eventos", {**EVENTO_OK, "nombre": "Otro evento", "fecha_inicio": "2099-01-01T10:00:00Z"})

    status, body = llamar("GET /eventos")
    assert status == 200
    assert [e["nombre"] for e in body["eventos"]] == ["Otro evento", "Concierto de bienvenida"]

    status, body = llamar("GET /eventos/{evento_id}", path={"evento_id": creado["evento_id"]})
    assert status == 200 and body["nombre"] == EVENTO_OK["nombre"]


def test_evento_inexistente(aws):
    status, _ = llamar("GET /eventos/{evento_id}", path={"evento_id": "no-existe"})
    assert status == 404


def test_ruta_desconocida(aws):
    status, _ = llamar("DELETE /eventos")
    assert status == 404


def test_pin_se_guarda_como_hash(aws):
    from paseqr.common import db

    _, creado = llamar("POST /eventos", EVENTO_OK)
    item = db.tabla_eventos().get_item(Key={"evento_id": creado["evento_id"]})["Item"]
    assert item["pin_hash"] == eventos.hash_pin(creado["evento_id"], "4321")
    assert "pin_staff" not in item
