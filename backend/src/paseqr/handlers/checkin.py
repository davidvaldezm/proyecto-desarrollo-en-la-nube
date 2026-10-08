"""Lambda `check-in` — Flujo 2 (responsable: Vittorio Catino).

POST /checkin
  Entrada: {"evento_id": str, "pin_staff": str, "qr": "boleto_id.evento_id.firma"}
  Pasos a implementar:
    1. Validar entrada y que el PIN coincida con pin_hash del evento
       (ver paseqr.handlers.eventos.hash_pin).
    2. Verificar la firma HMAC del QR con la llave de Secrets Manager (SECRETO_QR_ARN).
    3. Verificar que el boleto pertenezca a ese evento.
    4. update_item condicional: estado = USADO, usado_en = ahora
       SOLO SI estado = EMITIDO (evita doble entrada; si falla → 409 "ya usado").
  Respuesta: 200 {"resultado": "VALIDO" | "YA_USADO" | "INVALIDO" | "OTRO_EVENTO",
                  "asistentes": int}
"""
from paseqr.common.http import ApiError, api_handler


@api_handler
def handler(event, _context):
    raise ApiError(501, "Check-in pendiente de implementar (Flujo 2)")
