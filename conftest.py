"""
Fixtures compartidos y mocks de AWS para tests.
Usa moto para simular DynamoDB, S3, SES y Bedrock en us-east-1.
"""

import os
import pytest
import boto3
from moto import mock_aws


# Configurar variables de entorno antes de importar cualquier módulo
os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
os.environ["AWS_ACCESS_KEY_ID"] = "testing"
os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
os.environ["AWS_SECURITY_TOKEN"] = "testing"
os.environ["AWS_SESSION_TOKEN"] = "testing"

REGION = "us-east-1"


@pytest.fixture
def aws_credentials():
    """Credenciales ficticias para moto."""
    os.environ["AWS_DEFAULT_REGION"] = REGION
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"


@pytest.fixture
def dynamodb_resource(aws_credentials):
    """Cliente DynamoDB mockeado con las 4 tablas del proyecto."""
    with mock_aws():
        dynamodb = boto3.resource("dynamodb", region_name=REGION)
        _create_tables(dynamodb)
        yield dynamodb


@pytest.fixture
def dynamodb_client(aws_credentials):
    """Cliente DynamoDB (low-level) mockeado con las 4 tablas."""
    with mock_aws():
        client = boto3.client("dynamodb", region_name=REGION)
        resource = boto3.resource("dynamodb", region_name=REGION)
        _create_tables(resource)
        yield client


@pytest.fixture
def s3_client(aws_credentials):
    """Cliente S3 mockeado con bucket de archivos."""
    with mock_aws():
        s3 = boto3.client("s3", region_name=REGION)
        s3.create_bucket(Bucket="estimations-files")
        yield s3


@pytest.fixture
def ses_client(aws_credentials):
    """Cliente SES mockeado con identidad verificada."""
    with mock_aws():
        ses = boto3.client("ses", region_name=REGION)
        ses.verify_email_identity(EmailAddress="noreply@preventa.example.com")
        yield ses


@pytest.fixture
def bedrock_client(aws_credentials):
    """Cliente Bedrock Runtime mockeado."""
    with mock_aws():
        client = boto3.client("bedrock-runtime", region_name=REGION)
        yield client


def _create_tables(dynamodb):
    """Crea las 4 tablas DynamoDB del proyecto con sus GSIs."""

    # Tabla: conversations
    dynamodb.create_table(
        TableName="conversations",
        KeySchema=[
            {"AttributeName": "conversation_id", "KeyType": "HASH"},
            {"AttributeName": "user_id", "KeyType": "RANGE"},
        ],
        AttributeDefinitions=[
            {"AttributeName": "conversation_id", "AttributeType": "S"},
            {"AttributeName": "user_id", "AttributeType": "S"},
            {"AttributeName": "created_at", "AttributeType": "S"},
        ],
        GlobalSecondaryIndexes=[
            {
                "IndexName": "user_id-index",
                "KeySchema": [
                    {"AttributeName": "user_id", "KeyType": "HASH"},
                    {"AttributeName": "created_at", "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "ALL"},
            }
        ],
        BillingMode="PAY_PER_REQUEST",
    )

    # Tabla: estimations
    dynamodb.create_table(
        TableName="estimations",
        KeySchema=[
            {"AttributeName": "estimation_id", "KeyType": "HASH"},
        ],
        AttributeDefinitions=[
            {"AttributeName": "estimation_id", "AttributeType": "S"},
            {"AttributeName": "user_id", "AttributeType": "S"},
            {"AttributeName": "created_at", "AttributeType": "S"},
        ],
        GlobalSecondaryIndexes=[
            {
                "IndexName": "user_id-index",
                "KeySchema": [
                    {"AttributeName": "user_id", "KeyType": "HASH"},
                    {"AttributeName": "created_at", "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "ALL"},
            }
        ],
        BillingMode="PAY_PER_REQUEST",
    )

    # Tabla: pricing_cache
    dynamodb.create_table(
        TableName="pricing_cache",
        KeySchema=[
            {"AttributeName": "service_id", "KeyType": "HASH"},
            {"AttributeName": "component", "KeyType": "RANGE"},
        ],
        AttributeDefinitions=[
            {"AttributeName": "service_id", "AttributeType": "S"},
            {"AttributeName": "component", "AttributeType": "S"},
        ],
        BillingMode="PAY_PER_REQUEST",
    )

    # Tabla: partners
    dynamodb.create_table(
        TableName="partners",
        KeySchema=[
            {"AttributeName": "partner_id", "KeyType": "HASH"},
        ],
        AttributeDefinitions=[
            {"AttributeName": "partner_id", "AttributeType": "S"},
            {"AttributeName": "user_id", "AttributeType": "S"},
            {"AttributeName": "created_at", "AttributeType": "S"},
        ],
        GlobalSecondaryIndexes=[
            {
                "IndexName": "user_id-index",
                "KeySchema": [
                    {"AttributeName": "user_id", "KeyType": "HASH"},
                    {"AttributeName": "created_at", "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "ALL"},
            }
        ],
        BillingMode="PAY_PER_REQUEST",
    )
