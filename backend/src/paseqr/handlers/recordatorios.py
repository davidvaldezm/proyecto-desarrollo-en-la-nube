"""Lambda `recordatorios` — Flujo 3 (responsable: Juan Pablo Gutiérrez).

Disparador: regla de EventBridge cada hora. También se puede invocar a mano (demo):
  {"accion": "reporte", "evento_id": "..."}      genera el reporte de inmediato
  {"accion": "recordatorio", "evento_id": "..."} envía el recordatorio de inmediato

1. Recordatorio: eventos que empiezan en las próximas 24 h y aún no lo recibieron ->
   correo a cada asistente con boleto emitido.
2. Reporte: eventos que terminaron (6 h después del inicio) -> CSV con vendidos, asistentes,
   tasa de asistencia y hora pico en S3 + aviso al organizador con enlace de descarga.
"""
import csv
import io
import logging
from collections import Counter
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

from paseqr.common import aws, db
from paseqr.common.metrics import metrica

logger = logging.getLogger()
logger.setLevel(logging.INFO)
TZ = ZoneInfo("America/Mexico_City")
VENTANA_RECORDATORIO = timedelta(hours=24)
DURACION_EVENTO = timedelta(hours=6)


def _eventos() -> list[dict]:
    tabla, items, kwargs = db.tabla_eventos(), [], {}
    while True:
        page = tabla.scan(**kwargs)
        items.extend(page.get("Items", []))
        if "LastEvaluatedKey" not in page:
            return items
        kwargs["ExclusiveStartKey"] = page["LastEvaluatedKey"]


def _boletos(evento_id: str) -> list[dict]:
    tabla, items, kwargs = db.tabla_boletos(), [], {}
    while True:
        page = tabla.query(IndexName="por_evento", KeyConditionExpression=Key("evento_id").eq(evento_id), **kwargs)
        items.extend(page.get("Items", []))
        if "LastEvaluatedKey" not in page:
            return items
        kwargs["ExclusiveStartKey"] = page["LastEvaluatedKey"]


def _marcar(evento_id: str, campo: str) -> bool:
    """Marca el evento de forma condicional para no repetir el envío si dos ejecuciones coinciden."""
    try:
        db.tabla_eventos().update_item(
            Key={"evento_id": evento_id},
            UpdateExpression=f"SET {campo} = :t",
            ConditionExpression=f"attribute_not_exists({campo})",
            ExpressionAttributeValues={":t": datetime.now(timezone.utc).isoformat()},
        )
        return True
    except ClientError as err:
        if err.response["Error"]["Code"] == "ConditionalCheckFailedException":
            return False
        raise


def enviar_recordatorio(evento: dict) -> int:
    if not _marcar(evento["evento_id"], "recordatorio_enviado"):
        return 0
    inicio = datetime.fromisoformat(evento["fecha_inicio"]).astimezone(TZ).strftime("%d/%m/%Y a las %H:%M")
    correos = {b["email"]: b["nombre"] for b in _boletos(evento["evento_id"]) if b["estado"] == "EMITIDO"}
    for email, nombre in correos.items():
        aws.publicar_correo(
            email, f"Recordatorio: {evento['nombre']} es mañana",
            f"Hola {nombre}:\n\nTe recordamos que {evento['nombre']} es el {inicio} en {evento['lugar']}.\n"
            f"Lleva tu boleto con código QR (impreso o en el celular).\n\n— PaseQR",
        )
    metrica("RecordatoriosEnviados", len(correos))
    return len(correos)


def calcular_reporte(evento: dict, boletos: list[dict]) -> tuple[dict, str]:
    vendidos = len(boletos)
    usados = [b for b in boletos if b["estado"] == "USADO"]
    horas = Counter(datetime.fromisoformat(b["usado_en"]).astimezone(TZ).strftime("%H:00")
                    for b in usados if b.get("usado_en"))
    resumen = {
        "evento": evento["nombre"],
        "fecha": evento["fecha_inicio"],
        "cupo": int(evento["cupo"]),
        "vendidos": vendidos,
        "asistentes": len(usados),
        "tasa_asistencia": f"{(len(usados) / vendidos * 100):.1f}%" if vendidos else "0.0%",
        "hora_pico": horas.most_common(1)[0][0] if horas else "-",
        "ingresos": f"{float(evento.get('precio', 0)) * vendidos:.2f}",
    }
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["Reporte de asistencia PaseQR"])
    for k, v in resumen.items():
        w.writerow([k, v])
    w.writerow([])
    w.writerow(["boleto_id", "nombre", "email", "estado", "usado_en"])
    for b in sorted(boletos, key=lambda x: x["boleto_id"]):
        w.writerow([b["boleto_id"], b["nombre"], b["email"], b["estado"], b.get("usado_en", "")])
    return resumen, out.getvalue()


def generar_reporte(evento: dict, forzar: bool = False) -> dict | None:
    if not forzar and not _marcar(evento["evento_id"], "reporte_generado"):
        return None
    resumen, contenido = calcular_reporte(evento, _boletos(evento["evento_id"]))
    key = f"reportes/{evento['evento_id']}.csv"
    s3 = aws.client("s3")
    s3.put_object(Bucket=aws.env("BUCKET_BOLETOS"), Key=key, Body=contenido.encode("utf-8-sig"),
                  ContentType="text/csv")
    url = s3.generate_presigned_url("get_object", Params={"Bucket": aws.env("BUCKET_BOLETOS"), "Key": key},
                                    ExpiresIn=3600)
    if evento.get("organizador_email"):
        texto = "\n".join(f"  {k}: {v}" for k, v in resumen.items())
        aws.publicar_correo(evento["organizador_email"], f"Reporte de asistencia: {evento['nombre']}",
                            f"Resumen del evento:\n\n{texto}\n\nDescarga el CSV (válido 1 hora):\n{url}\n\n— PaseQR")
    db.tabla_eventos().update_item(Key={"evento_id": evento["evento_id"]},
                                   UpdateExpression="SET estado = :f, reporte_key = :k",
                                   ExpressionAttributeValues={":f": "FINALIZADO", ":k": key})
    metrica("ReportesGenerados")
    return {**resumen, "reporte_key": key}


def handler(event, _context):
    ahora = datetime.now(timezone.utc)
    accion, evento_id = event.get("accion"), event.get("evento_id")
    if accion and evento_id:  # invocación manual
        evento = db.tabla_eventos().get_item(Key={"evento_id": evento_id}).get("Item")
        if not evento:
            return {"error": "Evento no encontrado"}
        if accion == "reporte":
            return generar_reporte(evento, forzar=True)
        return {"recordatorios": enviar_recordatorio(evento)}

    recordatorios, reportes = 0, 0
    for evento in _eventos():
        inicio = datetime.fromisoformat(evento["fecha_inicio"])
        if evento.get("estado") == "A_LA_VENTA" and ahora < inicio <= ahora + VENTANA_RECORDATORIO \
                and "recordatorio_enviado" not in evento:
            recordatorios += enviar_recordatorio(evento)
        if evento.get("estado") == "A_LA_VENTA" and inicio + DURACION_EVENTO <= ahora:
            reportes += 1 if generar_reporte(evento) else 0
    logger.info("Recordatorios: %s, reportes: %s", recordatorios, reportes)
    return {"recordatorios": recordatorios, "reportes": reportes}
