"""Acceso a recursos de AWS. Los nombres llegan por variables de entorno definidas en Terraform."""
import os

import boto3


def _resource():
    return boto3.resource("dynamodb", region_name=os.environ.get("AWS_REGION", "us-east-1"))


def tabla_eventos():
    return _resource().Table(os.environ["TABLA_EVENTOS"])


def tabla_boletos():
    return _resource().Table(os.environ["TABLA_BOLETOS"])
