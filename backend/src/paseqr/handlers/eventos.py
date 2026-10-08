"""Lambda `eventos`: alta y consulta de eventos.

Rutas (API Gateway HTTP API):
  POST /eventos               crea un evento
  GET  /eventos               lista eventos a la venta
  GET  /eventos/{evento_id}   detalle de un evento
"""
import hashlib
import uuid
from datetime import datetime, timezone

from paseqr.common import db
from paseqr.common.http import ApiError, api_handler, parse_json_body, path_param, respond
from paseqr.common.validation import Validador

CAMPOS_PUBLICOS = (
    "evento_id", "nombre", "descripcion", "lugar", "fecha_inicio",
    "cupo", "vendidos", "precio", "estado", "creado_en",
)


def hash_pin(evento_id: str, pin: str) -> str:
    return hashlib.sha256(f"{evento_id}:{pin}".encode()).hexdigest()


def publico(item: dict) -> dict:
    data = {k: item[k] for k in CAMPOS_PUBLICOS if k in item}
    data["disponibles"] = int(item.get("cupo", 0)) - int(item.get("vendidos", 0))
    return data


def crear_evento(event):
    datos = (
        Validador(parse_json_body(event))
        .texto("nombre", 3, 120)
        .texto("descripcion", 0, 1000, requerido=False)
        .texto("lugar", 3, 200)
        .fecha_futura("fecha_inicio")
        .entero("cupo", 1, 5000)
        .dinero("precio")
        .email("organizador_email")
        .regex("pin_staff", r"\d{4,8}", "Debe ser un PIN de 4 a 8 dígitos")
        .resultado()
    )
    evento_id = str(uuid.uuid4())
    pin = datos.pop("pin_staff")
    item = {
        **datos,
        "evento_id": evento_id,
        "pin_hash": hash_pin(evento_id, pin),
        "vendidos": 0,
        "estado": "A_LA_VENTA",
        "creado_en": datetime.now(timezone.utc).isoformat(),
    }
    db.tabla_eventos().put_item(Item=item, ConditionExpression="attribute_not_exists(evento_id)")
    return respond(201, publico(item))


def listar_eventos(_event):
    tabla = db.tabla_eventos()
    items, kwargs = [], {}
    while True:  # scan paginado; suficiente para el volumen del proyecto
        page = tabla.scan(**kwargs)
        items.extend(page.get("Items", []))
        if "LastEvaluatedKey" not in page:
            break
        kwargs["ExclusiveStartKey"] = page["LastEvaluatedKey"]
    a_la_venta = [publico(i) for i in items if i.get("estado") == "A_LA_VENTA"]
    a_la_venta.sort(key=lambda e: e["fecha_inicio"])
    return respond(200, {"eventos": a_la_venta})


def obtener_evento(event):
    evento_id = path_param(event, "evento_id")
    item = db.tabla_eventos().get_item(Key={"evento_id": evento_id}).get("Item")
    if not item:
        raise ApiError(404, "Evento no encontrado")
    return respond(200, publico(item))


RUTAS = {
    "POST /eventos": crear_evento,
    "GET /eventos": listar_eventos,
    "GET /eventos/{evento_id}": obtener_evento,
}


@api_handler
def handler(event, _context):
    accion = RUTAS.get(event.get("routeKey"))
    if not accion:
        raise ApiError(404, "Ruta no encontrada")
    return accion(event)
