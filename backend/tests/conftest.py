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
        yield


def api_event(route_key: str, body=None, path_params=None) -> dict:
    """Construye un evento como el que manda API Gateway HTTP API (payload v2)."""
    return {
        "routeKey": route_key,
        "body": json.dumps(body) if body is not None else None,
        "pathParameters": path_params,
        "isBase64Encoded": False,
    }
