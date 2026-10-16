import json
import os
import sys
from pathlib import Path

import boto3
import pytest
from moto import mock_aws

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")
os.environ.setdefault("AWS_REGION", "us-east-1")
os.environ.setdefault("AWS_ACCESS_KEY_ID", "testing")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "testing")
os.environ["TABLA_EVENTOS"] = "test-eventos"
os.environ["TABLA_BOLETOS"] = "test-boletos"
os.environ["BUCKET_BOLETOS"] = "test-boletos-bucket"
os.environ["FRONTEND_URL"] = "http://paseqr.test"


@pytest.fixture
def aws():
    """DynamoDB simulado con moto, con las mismas tablas que crea Terraform."""
    with mock_aws():
        ddb = boto3.client("dynamodb", region_name="us-east-1")
        ddb.create_table(
            TableName="test-eventos",
            BillingMode="PAY_PER_REQUEST",
            AttributeDefinitions=[{"AttributeName": "evento_id", "AttributeType": "S"}],
            KeySchema=[{"AttributeName": "evento_id", "KeyType": "HASH"}],
        )
        ddb.create_table(
            TableName="test-boletos",
            BillingMode="PAY_PER_REQUEST",
            AttributeDefinitions=[
                {"AttributeName": "boleto_id", "AttributeType": "S"},
                {"AttributeName": "evento_id", "AttributeType": "S"},
                {"AttributeName": "email", "AttributeType": "S"},
            ],
            KeySchema=[{"AttributeName": "boleto_id", "KeyType": "HASH"}],
            GlobalSecondaryIndexes=[
                {"IndexName": "por_evento", "KeySchema": [{"AttributeName": "evento_id", "KeyType": "HASH"}],
                 "Projection": {"ProjectionType": "ALL"}},
                {"IndexName": "por_email", "KeySchema": [{"AttributeName": "email", "KeyType": "HASH"}],
                 "Projection": {"ProjectionType": "ALL"}},
            ],
        )
        sqs = boto3.client("sqs", region_name="us-east-1")
        os.environ["COLA_EMISION_URL"] = sqs.create_queue(QueueName="test-emision")["QueueUrl"]
        sns = boto3.client("sns", region_name="us-east-1")
        os.environ["TOPICO_NOTIFICACIONES"] = sns.create_topic(Name="test-notificaciones")["TopicArn"]
        boto3.client("s3", region_name="us-east-1").create_bucket(Bucket="test-boletos-bucket")
        sm = boto3.client("secretsmanager", region_name="us-east-1")
        os.environ["SECRETO_QR_ARN"] = sm.create_secret(Name="test-qr", SecretString="llave-de-prueba")["ARN"]
        from paseqr.common import qr
        qr._cache.clear()
        yield


def api_event(route_key: str, body=None, path_params=None) -> dict:
    """Construye un evento como el que manda API Gateway HTTP API (payload v2)."""
    return {
        "routeKey": route_key,
        "body": json.dumps(body) if body is not None else None,
        "pathParameters": path_params,
        "isBase64Encoded": False,
    }


def crear_evento(cupo=10, pin="4321", **extra) -> dict:
    """Crea un evento con la Lambda real y devuelve su JSON."""
    from paseqr.handlers import eventos
    body = {"nombre": "Concierto de prueba", "lugar": "Auditorio", "fecha_inicio": "2099-11-20T20:00:00-06:00",
            "cupo": cupo, "precio": 100, "organizador_email": "org@iteso.mx", "pin_staff": pin, **extra}
    resp = eventos.handler(api_event("POST /eventos", body), None)
    assert resp["statusCode"] == 201, resp
    return json.loads(resp["body"])


def procesar_cola() -> int:
    """Simula el disparador SQS -> generar-boleto: lee todos los mensajes y se los pasa a la Lambda."""
    from paseqr.handlers import generar_boleto
    sqs = boto3.client("sqs", region_name="us-east-1")
    total = 0
    while True:
        msgs = sqs.receive_message(QueueUrl=os.environ["COLA_EMISION_URL"], MaxNumberOfMessages=10).get("Messages", [])
        if not msgs:
            return total
        records = [{"messageId": m["MessageId"], "body": m["Body"]} for m in msgs]
        assert generar_boleto.handler({"Records": records}, None) == {"batchItemFailures": []}
        for m in msgs:
            sqs.delete_message(QueueUrl=os.environ["COLA_EMISION_URL"], ReceiptHandle=m["ReceiptHandle"])
        total += len(msgs)
