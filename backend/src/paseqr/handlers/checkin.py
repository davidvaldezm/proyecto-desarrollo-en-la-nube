"""Lambda `check-in` — Flujo 2 (responsable: Vittorio Catino).

POST /checkin  {"evento_id", "pin_staff", "qr": "v1.boleto_id.evento_id.firma"}

Validación en tres pasos (ver Tarea 2):
  1. Firma HMAC del QR (tiempo constante). Falsificado o alterado -> INVALIDO, sin tocar la base.
  2. El QR debe ser del evento que escanea el staff -> si no, OTRO_EVENTO.
  3. UpdateItem condicional EMITIDO -> USADO. Si dos puertas escanean el mismo QR a la vez,
     solo una cumple la condición; la otra recibe YA_USADO con la hora del primer uso.
"""
import hmac
from datetime import datetime, timezone

from botocore.exceptions import ClientError

from paseqr.common import db, qr
from paseqr.common.http import ApiError, api_handler, parse_json_body, respond
from paseqr.common.metrics import metrica
from paseqr.common.validation import Validador
from paseqr.handlers.eventos import hash_pin

MENSAJES = {
    "VALIDO": "Acceso permitido",
    "YA_USADO": "Este boleto ya se usó",
    "INVALIDO": "Código no válido",
    "OTRO_EVENTO": "El boleto es de otro evento",
    "NO_EMITIDO": "El boleto aún no se emite",
}


def _resultado(resultado: str, evento_id: str, asistentes: int, **extra):
    nombre_metrica = "CheckInsValidos" if resultado == "VALIDO" else "CheckInsRechazados"
    metrica(nombre_metrica, evento_id=evento_id, resultado=resultado)
    return respond(200, {"resultado": resultado, "mensaje": MENSAJES[resultado],
                         "asistentes": asistentes, **extra})


@api_handler
def handler(event, _context):
    datos = (
        Validador(parse_json_body(event))
        .texto("evento_id", 1, 64)
        .regex("pin_staff", r"\d{4,8}", "Debe ser un PIN de 4 a 8 dígitos")
        .texto("qr", 10, 300)
        .resultado()
    )
    evento_id = datos["evento_id"]
    evento = db.tabla_eventos().get_item(Key={"evento_id": evento_id}).get("Item")
    if not evento:
        raise ApiError(404, "Evento no encontrado")
    if not hmac.compare_digest(evento.get("pin_hash", ""), hash_pin(evento_id, datos["pin_staff"])):
        raise ApiError(403, "PIN incorrecto")
    asistentes = int(evento.get("asistentes", 0))

    # 1. Firma
    try:
        boleto_id, evento_qr = qr.verificar(datos["qr"])
    except qr.QRInvalido:
        return _resultado("INVALIDO", evento_id, asistentes)

    # 2. Evento correcto
    if evento_qr != evento_id:
        return _resultado("OTRO_EVENTO", evento_id, asistentes)

    # 3. Marcar como usado solo si estaba EMITIDO
    ahora = datetime.now(timezone.utc).isoformat()
    tabla = db.tabla_boletos()
    try:
        boleto = tabla.update_item(
            Key={"boleto_id": boleto_id},
            UpdateExpression="SET estado = :usado, usado_en = :t",
            ConditionExpression="estado = :emitido AND evento_id = :e",
            ExpressionAttributeValues={":usado": "USADO", ":emitido": "EMITIDO", ":e": evento_id, ":t": ahora},
            ReturnValues="ALL_NEW",
        )["Attributes"]
    except ClientError as err:
        if err.response["Error"]["Code"] != "ConditionalCheckFailedException":
            raise
        actual = tabla.get_item(Key={"boleto_id": boleto_id}).get("Item")
        if not actual:
            return _resultado("INVALIDO", evento_id, asistentes)
        if actual["estado"] == "USADO":
            return _resultado("YA_USADO", evento_id, asistentes, nombre=actual["nombre"],
                              usado_en=actual.get("usado_en"))
        return _resultado("NO_EMITIDO", evento_id, asistentes)

    asistentes = int(db.tabla_eventos().update_item(
        Key={"evento_id": evento_id},
        UpdateExpression="ADD asistentes :uno",
        ExpressionAttributeValues={":uno": 1},
        ReturnValues="UPDATED_NEW",
    )["Attributes"]["asistentes"])
    return _resultado("VALIDO", evento_id, asistentes, nombre=boleto["nombre"], usado_en=ahora)
