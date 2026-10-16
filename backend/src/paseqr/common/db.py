"""Acceso a DynamoDB. Los nombres de las tablas llegan por variables de entorno definidas en Terraform."""
import os

import boto3


def _resource():
    return boto3.resource("dynamodb", region_name=os.environ.get("AWS_REGION", "us-east-1"))


def nombre_tabla_eventos() -> str:
    return os.environ["TABLA_EVENTOS"]


def nombre_tabla_boletos() -> str:
    return os.environ["TABLA_BOLETOS"]


def tabla_eventos():
    return _resource().Table(nombre_tabla_eventos())


def tabla_boletos():
    return _resource().Table(nombre_tabla_boletos())
