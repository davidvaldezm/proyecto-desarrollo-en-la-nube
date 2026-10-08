"""Lambda `recordatorios` — Flujo 3 (responsable: Juan Pablo Gutiérrez).

Disparador: regla de EventBridge cada hora.
  Pasos a implementar:
    1. Buscar eventos que empiezan en las próximas 24-25 h y sin recordatorio enviado;
       publicar recordatorio en SNS (TOPICO_NOTIFICACIONES) y marcar `recordatorio_enviado`.
    2. Buscar eventos terminados sin reporte; calcular vendidos, asistentes, tasa de
       asistencia y hora pico; guardar CSV en S3 (BUCKET_BOLETOS, prefijo reportes/)
       y avisar al organizador por SNS con una URL prefirmada.
"""
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def handler(event, _context):
    logger.info("Ejecución programada (pendiente de implementar): %s", event.get("time"))
    return {"recordatorios": 0, "reportes": 0}
