"""Lambda `generar-boleto` — Flujo 1, consumidor de SQS (responsable: David Valdez).

Por cada mensaje {"boleto_id"}: firma el QR, genera el PDF, lo guarda en S3, marca el boleto
como EMITIDO y avisa al comprador por SNS.

Idempotente (SQS entrega "al menos una vez"): la llave del PDF en S3 es fija y el cambio
PENDIENTE -> EMITIDO lleva condición, así que un mensaje repetido no tiene efecto.
Los mensajes que fallan se reportan en batchItemFailures; tras 3 intentos van a la DLQ.
"""
import io
import json
import logging
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from botocore.exceptions import ClientError
from reportlab.graphics import renderPDF
from reportlab.graphics.barcode.qr import QrCodeWidget
from reportlab.graphics.shapes import Drawing
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from paseqr.common import aws, db, qr
from paseqr.common.metrics import metrica

logger = logging.getLogger()
logger.setLevel(logging.INFO)
NARANJA = HexColor("#EA580C")
TZ = ZoneInfo("America/Mexico_City")


def fecha_legible(iso: str) -> str:
    fecha = datetime.fromisoformat(iso).astimezone(TZ)
    return fecha.strftime("%d/%m/%Y %H:%M") + " (hora del centro de México)"


def crear_pdf(boleto: dict, contenido_qr: str) -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    ancho, alto = letter
    c.setTitle(f"Boleto {boleto['evento_nombre']}")

    c.setFillColor(NARANJA)
    c.rect(0, alto - 90, ancho, 90, stroke=0, fill=1)
    c.setFillColor(HexColor("#FFFFFF"))
    c.setFont("Helvetica-Bold", 28)
    c.drawString(50, alto - 58, "PaseQR")
    c.setFont("Helvetica", 12)
    c.drawRightString(ancho - 50, alto - 55, "Boleto digital")

    c.setFillColor(HexColor("#0F172A"))
    c.setFont("Helvetica-Bold", 22)
    c.drawString(50, alto - 140, boleto["evento_nombre"][:45])
    c.setFont("Helvetica", 13)
    lineas = [
        f"Fecha: {fecha_legible(boleto['fecha_evento'])}",
        f"Lugar: {boleto.get('lugar', '')}",
        f"Asistente: {boleto['nombre']}",
        f"Boleto: {boleto.get('numero', 1)}  ·  ID {boleto['boleto_id']}",
    ]
    for i, linea in enumerate(lineas):
        c.drawString(50, alto - 175 - i * 22, linea[:90])

    widget = QrCodeWidget(contenido_qr, barLevel="M")
    x1, y1, x2, y2 = widget.getBounds()
    lado = 260
    dibujo = Drawing(lado, lado, transform=[lado / (x2 - x1), 0, 0, lado / (y2 - y1), 0, 0])
    dibujo.add(widget)
    renderPDF.draw(dibujo, c, (ancho - lado) / 2, alto - 590)

    c.setFont("Helvetica", 10)
    c.setFillColor(HexColor("#475569"))
    c.drawCentredString(ancho / 2, alto - 610, "Presenta este código en la entrada. Es válido para una sola persona.")
    c.drawCentredString(ancho / 2, alto - 625, "El código está firmado digitalmente: cualquier modificación lo invalida.")
    c.showPage()
    c.save()
    return buf.getvalue()


def procesar(boleto_id: str) -> None:
    tabla = db.tabla_boletos()
    boleto = tabla.get_item(Key={"boleto_id": boleto_id}).get("Item")
    if not boleto:
        logger.warning("Boleto %s no existe; se ignora", boleto_id)
        return
    if boleto["estado"] != "PENDIENTE":
        logger.info("Boleto %s ya está %s; mensaje duplicado", boleto_id, boleto["estado"])
        return

    contenido = qr.firmar(boleto_id, boleto["evento_id"])
    pdf_key = f"boletos/{boleto['evento_id']}/{boleto_id.replace('#', '-')}.pdf"
    aws.client("s3").put_object(
        Bucket=aws.env("BUCKET_BOLETOS"), Key=pdf_key, Body=crear_pdf(boleto, contenido),
        ContentType="application/pdf",
    )
    try:
        tabla.update_item(
            Key={"boleto_id": boleto_id},
            UpdateExpression="SET estado = :emitido, pdf_key = :k, emitido_en = :t",
            ConditionExpression="estado = :pendiente",
            ExpressionAttributeValues={":emitido": "EMITIDO", ":pendiente": "PENDIENTE", ":k": pdf_key,
                                       ":t": datetime.now(timezone.utc).isoformat()},
        )
    except ClientError as err:
        if err.response["Error"]["Code"] == "ConditionalCheckFailedException":
            return  # otra ejecución lo emitió primero
        raise

    metrica("BoletosEmitidos", evento_id=boleto["evento_id"])
    try:
        aws.publicar_correo(
            boleto["email"],
            f"Tu boleto para {boleto['evento_nombre']}",
            f"Hola {boleto['nombre']}:\n\nTu boleto para {boleto['evento_nombre']} "
            f"({fecha_legible(boleto['fecha_evento'])}, {boleto.get('lugar', '')}) está listo.\n\n"
            f"Descárgalo en: {aws.env('FRONTEND_URL', '')}/#/mis-boletos\n\n— PaseQR",
        )
    except ClientError:
        logger.warning("No se pudo publicar la notificación de %s", boleto_id, exc_info=True)


def handler(event, _context):
    fallas = []
    for record in event.get("Records", []):
        try:
            procesar(json.loads(record["body"])["boleto_id"])
        except Exception:  # noqa: BLE001 - se reintenta solo este mensaje
            logger.exception("Error procesando %s", record.get("messageId"))
            fallas.append({"itemIdentifier": record["messageId"]})
    return {"batchItemFailures": fallas}
