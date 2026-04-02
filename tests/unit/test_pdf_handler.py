"""Tests unitarios para el handler de PDF/CSV."""

import json

import boto3
import pytest
from moto import mock_aws

from src.handlers.pdf_handler import handler
from src.models.estimation import Estimation
from src.models.partner import PartnerData
from src.services import estimation_repo


def _create_tables_and_bucket(dynamodb, s3_client):
    """Crear tablas DynamoDB y bucket S3 para tests."""
    dynamodb.create_table(
        TableName="estimations",
        KeySchema=[{"AttributeName": "estimation_id", "KeyType": "HASH"}],
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
    s3_client.create_bucket(Bucket="estimations-files")


def _save_test_estimation(dynamodb):
    """Guardar estimación de prueba y retornar su ID."""
    estimation = Estimation(
        estimation_id="est-pdf-001",
        conversation_id="conv-001",
        user_id="user-001",
        service="amazon_connect",
        partner_data=PartnerData(
            partner_name="Test Partner",
            partner_email="test@example.com",
            region="US",
            end_customer="End Customer",
        ),
        monthly_cost=1000.0,
        annual_cost=12000.0,
        breakdown=[
            {"component": "License", "unit_price": 100.0, "quantity": 10, "monthly_cost": 1000.0}
        ],
        assumptions=["10 agents"],
        pricing_date="2024-01-15T00:00:00+00:00",
        created_at="2024-01-20T10:00:00+00:00",
    )
    estimation_repo.save_estimation(dynamodb, estimation)
    return estimation.estimation_id


class TestPdfHandler:
    """Tests para el handler de PDF."""

    @mock_aws
    def test_generate_pdf_success(self):
        """Generar PDF exitosamente retorna URL pre-firmada."""
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        s3_client = boto3.client("s3", region_name="us-east-1")
        _create_tables_and_bucket(dynamodb, s3_client)
        est_id = _save_test_estimation(dynamodb)

        event = {
            "pathParameters": {"id": est_id},
            "body": json.dumps({"format": "pdf", "language": "es"}),
        }
        result = handler(event, None)
        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert "file_url" in body
        assert body["file_key"].endswith(".pdf")
        assert body["expires_in"] == 3600

    @mock_aws
    def test_generate_csv_success(self):
        """Generar CSV exitosamente retorna URL pre-firmada."""
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        s3_client = boto3.client("s3", region_name="us-east-1")
        _create_tables_and_bucket(dynamodb, s3_client)
        est_id = _save_test_estimation(dynamodb)

        event = {
            "pathParameters": {"id": est_id},
            "body": json.dumps({"format": "csv", "language": "es"}),
        }
        result = handler(event, None)
        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert body["file_key"].endswith(".csv")

    @mock_aws
    def test_estimation_not_found(self):
        """Estimación no encontrada retorna 404."""
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        s3_client = boto3.client("s3", region_name="us-east-1")
        _create_tables_and_bucket(dynamodb, s3_client)

        event = {
            "pathParameters": {"id": "nonexistent"},
            "body": json.dumps({"format": "pdf"}),
        }
        result = handler(event, None)
        assert result["statusCode"] == 404

    def test_missing_estimation_id(self):
        """estimation_id faltante retorna 400."""
        event = {
            "pathParameters": {},
            "body": json.dumps({"format": "pdf"}),
        }
        result = handler(event, None)
        assert result["statusCode"] == 400

    def test_invalid_format(self):
        """Formato inválido retorna 400."""
        event = {
            "pathParameters": {"id": "est-001"},
            "body": json.dumps({"format": "xlsx"}),
        }
        result = handler(event, None)
        assert result["statusCode"] == 400

    def test_invalid_body_json(self):
        """Body JSON inválido retorna 400."""
        event = {
            "pathParameters": {"id": "est-001"},
            "body": "not-json{",
        }
        result = handler(event, None)
        assert result["statusCode"] == 400
