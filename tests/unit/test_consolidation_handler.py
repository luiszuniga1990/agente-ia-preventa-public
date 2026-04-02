"""Tests unitarios para el handler de consolidación."""

import json

import boto3
import pytest
from moto import mock_aws

from src.handlers.consolidation_handler import handler
from src.models.estimation import Estimation
from src.models.partner import PartnerData
from src.services import estimation_repo


def _setup_dynamodb():
    """Crear tabla estimations y guardar estimación de prueba."""
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
    estimation = Estimation(
        estimation_id="est-cons-001",
        conversation_id="conv-001",
        user_id="user-001",
        service="amazon_quick",
        partner_data=PartnerData(
            partner_name="Partner",
            partner_email="p@example.com",
            region="US",
            end_customer="Customer",
        ),
        monthly_cost=800.0,
        annual_cost=9600.0,
        breakdown=[{"component": "Base", "unit_price": 800.0, "quantity": 1, "monthly_cost": 800.0}],
        assumptions=["Standard usage"],
        pricing_date="2024-01-15T00:00:00+00:00",
        created_at="2024-01-20T10:00:00+00:00",
    )
    estimation_repo.save_estimation(dynamodb, estimation)
    return dynamodb


class TestConsolidationHandler:
    """Tests para el handler de consolidación."""

    @mock_aws
    def test_consolidate_success(self):
        """Consolidación exitosa retorna 200 con estimación consolidada."""
        _setup_dynamodb()
        event = {
            "pathParameters": {"id": "est-cons-001"},
            "body": json.dumps({
                "external_json": {
                    "external_services": [
                        {
                            "service_name": "External SaaS",
                            "provider": "Vendor",
                            "monthly_cost": 200.0,
                            "annual_cost": 2400.0,
                        }
                    ]
                }
            }),
        }
        result = handler(event, None)
        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert body["is_consolidated"] is True
        assert body["monthly_cost"] == 1000.0

    @mock_aws
    def test_estimation_not_found(self):
        """Estimación no encontrada retorna 404."""
        _setup_dynamodb()
        event = {
            "pathParameters": {"id": "nonexistent"},
            "body": json.dumps({"external_json": {"external_services": []}}),
        }
        result = handler(event, None)
        assert result["statusCode"] == 404

    def test_invalid_json_body(self):
        """Body JSON inválido retorna 400."""
        event = {
            "pathParameters": {"id": "est-001"},
            "body": "not valid json{{{",
        }
        result = handler(event, None)
        assert result["statusCode"] == 400

    def test_empty_body(self):
        """Body vacío retorna 400."""
        event = {
            "pathParameters": {"id": "est-001"},
            "body": "",
        }
        result = handler(event, None)
        assert result["statusCode"] == 400

    def test_missing_external_json(self):
        """external_json faltante retorna 400."""
        event = {
            "pathParameters": {"id": "est-001"},
            "body": json.dumps({"other_field": "value"}),
        }
        result = handler(event, None)
        assert result["statusCode"] == 400

    def test_body_too_large(self):
        """Body > 1 MB retorna 400."""
        large_body = "x" * (1_048_577)
        event = {
            "pathParameters": {"id": "est-001"},
            "body": large_body,
        }
        result = handler(event, None)
        assert result["statusCode"] == 400

    def test_missing_estimation_id(self):
        """estimation_id faltante retorna 400."""
        event = {
            "pathParameters": {},
            "body": json.dumps({"external_json": {}}),
        }
        result = handler(event, None)
        assert result["statusCode"] == 400
