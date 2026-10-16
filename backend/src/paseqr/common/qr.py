"""Firma y verificación de los códigos QR (compartido por el Flujo 1 y el Flujo 2).

Formato: v1.<boleto_id>.<evento_id>.<firma>
  firma = base64url(HMAC-SHA256(llave, "v1.<boleto_id>.<evento_id>")) sin relleno.
La llave vive en Secrets Manager y se guarda en memoria por contenedor de Lambda.
"""
import base64
import hashlib
import hmac

from . import aws

VERSION = "v1"
_cache: dict[str, bytes] = {}


class QRInvalido(Exception):
    pass


def _llave() -> bytes:
    arn = aws.env("SECRETO_QR_ARN")
    if arn not in _cache:
        valor = aws.client("secretsmanager").get_secret_value(SecretId=arn)["SecretString"]
        _cache[arn] = valor.encode()
    return _cache[arn]


def _firma(mensaje: str) -> str:
    digest = hmac.new(_llave(), mensaje.encode(), hashlib.sha256).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode()


def firmar(boleto_id: str, evento_id: str) -> str:
    for valor in (boleto_id, evento_id):
        if "." in valor:
            raise ValueError("Los IDs no pueden contener puntos")
    mensaje = f"{VERSION}.{boleto_id}.{evento_id}"
    return f"{mensaje}.{_firma(mensaje)}"


def verificar(qr: str) -> tuple[str, str]:
    """Devuelve (boleto_id, evento_id) si la firma es válida; si no, lanza QRInvalido."""
    partes = (qr or "").strip().split(".")
    if len(partes) != 4 or partes[0] != VERSION:
        raise QRInvalido("Formato de QR desconocido")
    version, boleto_id, evento_id, firma = partes
    esperada = _firma(f"{version}.{boleto_id}.{evento_id}")
    if not hmac.compare_digest(esperada, firma):  # tiempo constante
        raise QRInvalido("Firma inválida")
    return boleto_id, evento_id
