"""Utilidades HTTP compartidas por los handlers de API Gateway (HTTP API, payload v2)."""
import base64
import functools
import json
import logging
from decimal import Decimal

logger = logging.getLogger()
logger.setLevel(logging.INFO)


class ApiError(Exception):
    """Error controlado que se convierte en una respuesta HTTP."""

    def __init__(self, status: int, mensaje: str, detalles=None):
        super().__init__(mensaje)
        self.status = status
        self.mensaje = mensaje
        self.detalles = detalles


def _json_default(valor):
    if isinstance(valor, Decimal):
        return int(valor) if valor == valor.to_integral_value() else float(valor)
    raise TypeError(f"No serializable: {type(valor)}")


def respond(status: int, body) -> dict:
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body, default=_json_default, ensure_ascii=False),
    }


def parse_json_body(event: dict) -> dict:
    raw = event.get("body")
    if not raw:
        raise ApiError(400, "El cuerpo de la petición está vacío")
    if event.get("isBase64Encoded"):
        raw = base64.b64decode(raw).decode("utf-8")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ApiError(400, "El cuerpo no es JSON válido") from exc
    if not isinstance(data, dict):
        raise ApiError(400, "El cuerpo debe ser un objeto JSON")
    return data


def path_param(event: dict, nombre: str) -> str:
    valor = (event.get("pathParameters") or {}).get(nombre)
    if not valor:
        raise ApiError(400, f"Falta el parámetro '{nombre}' en la ruta")
    return valor


def api_handler(fn):
    """Decorador: convierte ApiError en respuestas 4xx y excepciones inesperadas en 500."""

    @functools.wraps(fn)
    def wrapper(event, context):
        try:
            return fn(event, context)
        except ApiError as err:
            body = {"error": err.mensaje}
            if err.detalles:
                body["detalles"] = err.detalles
            return respond(err.status, body)
        except Exception:  # noqa: BLE001 - queremos registrar cualquier falla
            logger.exception("Error no controlado")
            return respond(500, {"error": "Error interno del servidor"})

    return wrapper
