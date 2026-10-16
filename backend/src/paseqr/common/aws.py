"""Clientes de AWS y configuración leída de variables de entorno (definidas en Terraform)."""
import os

import boto3


def region() -> str:
    return os.environ.get("AWS_REGION", "us-east-1")


def client(servicio: str):
    return boto3.client(servicio, region_name=region())


def env(nombre: str, default: str | None = None) -> str:
    valor = os.environ.get(nombre, default)
    if valor is None:
        raise RuntimeError(f"Falta la variable de entorno {nombre}")
    return valor


def publicar_correo(email: str, asunto: str, mensaje: str) -> None:
    """Publica en el tópico de notificaciones; la suscripción del correo filtra por el atributo `email`."""
    client("sns").publish(
        TopicArn=env("TOPICO_NOTIFICACIONES"),
        Subject=asunto[:100],
        Message=mensaje,
        MessageAttributes={"email": {"DataType": "String", "StringValue": email}},
    )


def suscribir_correo(email: str) -> None:
    """Suscribe el correo al tópico con un filtro para que solo reciba sus mensajes.
    SNS manda un correo de confirmación la primera vez; si ya existe la suscripción no pasa nada."""
    client("sns").subscribe(
        TopicArn=env("TOPICO_NOTIFICACIONES"),
        Protocol="email",
        Endpoint=email,
        Attributes={"FilterPolicy": f'{{"email": ["{email}"]}}'},
    )
