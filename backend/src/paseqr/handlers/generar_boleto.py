"""Lambda `generar-boleto` — Flujo 1, consumidor de SQS (responsable: David Valdez).

Disparador: cola SQS `cola-emision` (lotes de hasta 10 mensajes).
  Pasos a implementar:
    1. Leer {"boleto_id"} de cada mensaje.
    2. Firmar el contenido del QR con HMAC-SHA256 usando la llave de Secrets Manager
       (SECRETO_QR_ARN) → payload "boleto_id.evento_id.firma".
    3. Generar el PDF con el QR (qrcode + reportlab) y subirlo a S3 (BUCKET_BOLETOS).
    4. Marcar el boleto como EMITIDO con la llave del PDF en S3.
    5. Publicar en SNS (TOPICO_NOTIFICACIONES) la confirmación.
  Reportar fallos parciales con `batchItemFailures` para que SQS reintente solo esos
  mensajes; tras 3 intentos terminan en la DLQ.
"""
import json
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def handler(event, _context):
    for record in event.get("Records", []):
        logger.info("Mensaje recibido (pendiente de procesar): %s", json.loads(record["body"]))
    return {"batchItemFailures": []}
