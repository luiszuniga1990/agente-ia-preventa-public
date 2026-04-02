"""Tests unitarios para el handler de email."""

import json

import boto3
import pytest
from moto import mock_aws

from src.handlers.email_handler import handler
from src.models.estimation import Estimation
from src.models.partner import PartnerData
from src.services import estimation_repo


def _setup_resources():
    """Crear tabla estimations, verificar SES y guardar estimación de prueba."""
    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
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
    ses = boto3.client("ses", region_name="us-east-1")
    ses.verify_email_identity(EmailAddress="noreply@preventa.example.com")

    estimation = Estimation(
        estimation_id="est-email-handler-001",
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
    return dynamodb


class TestEmailHandler:
    """Tests para el handler de email."""

    @mock_aws
    def test_send_email_success(self):
        """Envío exitoso retorna 200 con message_id."""
        _setup_resources()
        event = {
            "pathParameters": {"id": "est-email-handler-001"},
            "body": json.dumps({
                "recipient_email": "user@example.com",
                "language": "es",
            }),
        }
        result = handler(event, None)
        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert body["status"] == "sent"
        assert "message_id" in body

    @mock_aws
    def test_estimation_not_found(self):
        """Estimación no encontrada retorna 404."""
        _setup_resources()
        event = {
            "pathParameters": {"id": "nonexistent"},
            "body": json.dumps({"recipient_email": "user@example.com"}),
        }
        result = handler(event, None)
        assert result["statusCode"] == 404

    def test_missing_estimation_id(self):
        """estimation_id faltante retorna 400."""
        event = {
            "pathParameters": {},
            "body": json.dumps({"recipient_email": "user@example.com"}),
        }
        result = handler(event, None)
        assert result["statusCode"] == 400

    def test_missing_recipient_email(self):
        """recipient_email faltante retorna 400."""
        event = {
            "pathParameters": {"id": "est-001"},
            "body": json.dumps({"language": "es"}),
        }
        result = handler(event, None)
        assert result["statusCode"] == 400

    def test_invalid_body_json(self):
        """Body JSON inválido retorna 400."""
        event = {
            "pathParameters": {"id": "est-001"},
            "body": "invalid json{",
        }
        result = handler(event, None)
        assert result["statusCode"] == 400
