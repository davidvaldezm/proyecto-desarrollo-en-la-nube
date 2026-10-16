"""Lambda `comprar-boleto` — Flujo 1 (responsable: David Valdez).

POST /compras   {"compra_id": uuid, "evento_id", "nombre", "email", "cantidad": 1-4}
GET  /boletos?email=...   boletos del comprador con URL de descarga del PDF

Evita la sobreventa y las compras duplicadas (ver Tarea 2):
  * Una transacción de DynamoDB actualiza `vendidos` del evento SOLO si hay cupo y crea
    los boletos SOLO si no existen. O pasa todo o no pasa nada.
  * `compra_id` lo genera el frontend: se usa como ClientRequestToken y para derivar IDs
    deterministas (compra_id#1, compra_id#2...). Un reintento devuelve los mismos boletos.
"""
import json
import logging
import random
import time
from datetime import datetime, timezone

from boto3.dynamodb.conditions import Key
from boto3.dynamodb.types import TypeSerializer
from botocore.exceptions import ClientError

from paseqr.common import aws, db
from paseqr.common.http import ApiError, api_handler, parse_json_body, respond
from paseqr.common.metrics import metrica
from paseqr.common.validation import Validador

logger = logging.getLogger()
UUID_RE = r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
MAX_POR_COMPRA = 4
REINTENTOS_CONFLICTO = 5
_ser = TypeSerializer()


def _av(valor) -> dict:
    return _ser.serialize(valor)


def _boletos_de_compra(compra_id: str, cantidad: int) -> list[dict]:
    tabla = db.tabla_boletos()
    items = []
    for i in range(1, cantidad + 1):
        item = tabla.get_item(Key={"boleto_id": f"{compra_id}#{i}"}).get("Item")
        if item:
            items.append({"boleto_id": item["boleto_id"], "estado": item["estado"]})
    return items


def comprar(event):
    datos = (
        Validador(parse_json_body(event))
        .regex("compra_id", UUID_RE, "Debe ser un UUID")
        .regex("evento_id", UUID_RE, "Debe ser un UUID")
        .texto("nombre", 2, 120)
        .email("email")
        .entero("cantidad", 1, MAX_POR_COMPRA)
        .resultado()
    )
    compra_id, cantidad = datos["compra_id"].lower(), datos["cantidad"]

    evento = db.tabla_eventos().get_item(Key={"evento_id": datos["evento_id"]}).get("Item")
    if not evento:
        raise ApiError(404, "Evento no encontrado")
    if evento.get("estado") != "A_LA_VENTA":
        raise ApiError(409, "El evento ya no está a la venta")

    cupo = int(evento["cupo"])
    ahora = datetime.now(timezone.utc).isoformat()
    acciones = [{
        "Update": {
            "TableName": db.nombre_tabla_eventos(),
            "Key": {"evento_id": _av(evento["evento_id"])},
            # DynamoDB no permite aritmética en condiciones: vendidos + n <= cupo
            # equivale a vendidos <= cupo - n.
            "UpdateExpression": "SET vendidos = vendidos + :n",
            "ConditionExpression": "estado = :venta AND vendidos <= :limite",
            "ExpressionAttributeValues": {":n": _av(cantidad), ":limite": _av(cupo - cantidad),
                                          ":venta": _av("A_LA_VENTA")},
        }
    }]
    for i in range(1, cantidad + 1):
        acciones.append({
            "Put": {
                "TableName": db.nombre_tabla_boletos(),
                "Item": {k: _av(v) for k, v in {
                    "boleto_id": f"{compra_id}#{i}",
                    "compra_id": compra_id,
                    "numero": i,
                    "evento_id": evento["evento_id"],
                    "evento_nombre": evento["nombre"],
                    "fecha_evento": evento["fecha_inicio"],
                    "lugar": evento["lugar"],
                    "nombre": datos["nombre"],
                    "email": datos["email"],
                    "estado": "PENDIENTE",
                    "creado_en": ahora,
                }.items()},
                "ConditionExpression": "attribute_not_exists(boleto_id)",
            }
        })

    # Si otra transacción toca el mismo evento al mismo tiempo, DynamoDB cancela con
    # TransactionConflict: se reintenta con espera exponencial y jitter. Los reintentos no
    # usan ClientRequestToken; la idempotencia la siguen garantizando los IDs deterministas.
    for intento in range(REINTENTOS_CONFLICTO):
        try:
            kwargs = {"ClientRequestToken": compra_id} if intento == 0 else {}
            aws.client("dynamodb").transact_write_items(TransactItems=acciones, **kwargs)
            break
        except ClientError as err:
            if err.response["Error"]["Code"] != "TransactionCanceledException":
                raise
            razones = [r.get("Code") for r in err.response.get("CancellationReasons", [])]
            if any(r == "ConditionalCheckFailed" for r in razones[1:]):
                # Los boletos ya existen: es un reintento de la misma compra.
                existentes = _boletos_de_compra(compra_id, cantidad)
                if existentes:
                    return respond(200, {"compra_id": compra_id, "boletos": existentes, "reintento": True})
            if razones and razones[0] == "ConditionalCheckFailed":
                metrica("ComprasRechazadasPorCupo", evento_id=evento["evento_id"])
                actual = db.tabla_eventos().get_item(Key={"evento_id": evento["evento_id"]}).get("Item") or evento
                disponibles = max(cupo - int(actual.get("vendidos", 0)), 0)
                raise ApiError(409, "No hay lugares suficientes", {"disponibles": disponibles}) from err
            if "TransactionConflict" in razones and intento < REINTENTOS_CONFLICTO - 1:
                metrica("ConflictosDeCompra", evento_id=evento["evento_id"])
                time.sleep(random.uniform(0, 0.05 * 2 ** intento))
                continue
            if "TransactionConflict" in razones:
                raise ApiError(503, "Mucha demanda en este momento, intenta de nuevo") from err
            raise

    # La generación del PDF es asíncrona: un mensaje por boleto a la cola.
    aws.client("sqs").send_message_batch(
        QueueUrl=aws.env("COLA_EMISION_URL"),
        Entries=[{"Id": str(i), "MessageBody": json.dumps({"boleto_id": f"{compra_id}#{i}"})}
                 for i in range(1, cantidad + 1)],
    )
    try:
        aws.suscribir_correo(datos["email"])
    except ClientError:
        logger.warning("No se pudo suscribir %s a SNS", datos["email"], exc_info=True)

    metrica("BoletosVendidos", cantidad, evento_id=evento["evento_id"])
    boletos = [{"boleto_id": f"{compra_id}#{i}", "estado": "PENDIENTE"} for i in range(1, cantidad + 1)]
    return respond(202, {"compra_id": compra_id, "boletos": boletos})


def mis_boletos(event):
    params = event.get("queryStringParameters") or {}
    email = Validador(params).email("email").resultado()["email"]
    resp = db.tabla_boletos().query(IndexName="por_email", KeyConditionExpression=Key("email").eq(email))
    s3 = aws.client("s3")
    boletos = []
    for b in sorted(resp.get("Items", []), key=lambda x: x.get("creado_en", ""), reverse=True):
        item = {k: b.get(k) for k in ("boleto_id", "evento_nombre", "fecha_evento", "lugar", "nombre",
                                      "estado", "usado_en", "numero")}
        if b.get("pdf_key") and b["estado"] in ("EMITIDO", "USADO"):
            item["pdf_url"] = s3.generate_presigned_url(
                "get_object", Params={"Bucket": aws.env("BUCKET_BOLETOS"), "Key": b["pdf_key"]}, ExpiresIn=3600)
        boletos.append(item)
    return respond(200, {"boletos": boletos})


RUTAS = {"POST /compras": comprar, "GET /boletos": mis_boletos}


@api_handler
def handler(event, _context):
    accion = RUTAS.get(event.get("routeKey"))
    if not accion:
        raise ApiError(404, "Ruta no encontrada")
    return accion(event)
