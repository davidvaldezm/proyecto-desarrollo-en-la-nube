"""Lambda `comprar-boleto` — Flujo 1 (responsable: David Valdez).

POST /compras
  Entrada: {"evento_id": str, "nombre": str, "email": str, "cantidad": int (1-4)}
  Pasos a implementar:
    1. Validar entrada con Validador (nombre, email, cantidad 1-4).
    2. Verificar que el evento exista y esté A_LA_VENTA.
    3. update_item condicional en Eventos: vendidos = vendidos + cantidad
       SOLO SI vendidos + cantidad <= cupo  (evita sobreventa; si falla → 409).
    4. Crear N boletos en Boletos con estado PENDIENTE.
    5. Enviar un mensaje a SQS (COLA_EMISION_URL) por boleto: {"boleto_id": ...}.
  Respuesta: 202 {"boletos": [{"boleto_id", "estado": "PENDIENTE"}]}
"""
from paseqr.common.http import ApiError, api_handler


@api_handler
def handler(event, _context):
    raise ApiError(501, "Compra de boletos pendiente de implementar (Flujo 1)")
