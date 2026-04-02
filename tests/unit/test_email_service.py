"""Tests unitarios para el servicio de email."""

import email
from email.mime.multipart import MIMEMultipart

import boto3
import pytest
from moto import mock_aws

from src.models.estimation import Estimation
from src.models.partner import PartnerData
from src.services.email_service import (
    _build_plain_text_body,
    send_estimation_email,
)


def _make_estimation(**overrides) -> Estimation:
    """Crear estimación de prueba."""
    defaults = {
        "estimation_id": "est-email-001",
        "conversation_id": "conv-001",
        "user_id": "user-001",
        "service": "amazon_connect",
        "partner_data": PartnerData(
            partner_name="Acme Corp",
            partner_email="acme@example.com",
            region="LATAM",
            end_customer="Cliente Final SA",
        ),
        "monthly_cost": 1500.0,
        "annual_cost": 18000.0,
        "breakdown": [
            {"component": "License", "unit_price": 100.0, "quantity": 10, "monthly_cost": 1000.0},
            {"component": "Telephony", "unit_price": 50.0, "quantity": 10, "monthly_cost": 500.0},
        ],
        "assumptions": ["10 agentes concurrentes"],
        "pricing_date": "2024-01-15T00:00:00+00:00",
        "created_at": "2024-01-20T10:00:00+00:00",
    }
    defaults.update(overrides)
    return Estimation(**defaults)


class TestBuildPlainTextBody:
    """Tests para _build_plain_text_body."""

    def test_contains_partner_data(self):
        """Cuerpo debe contener datos del partner."""
        estimation = _make_estimation()
        body = _build_plain_text_body(estimation, "es")
        assert "Acme Corp" in body
        assert "acme@example.com" in body
        assert "LATAM" in body
        assert "Cliente Final SA" in body

    def test_contains_cost_breakdown(self):
        """Cuerpo debe contener desglose de costos."""
        estimation = _make_estimation()
        body = _build_plain_text_body(estimation, "es")
        assert "License" in body
        assert "Telephony" in body
        assert "$1,500.00" in body
        assert "$18,000.00" in body

    def test_contains_assumptions(self):
        """Cuerpo debe contener supuestos."""
        estimation = _make_estimation()
        body = _build_plain_text_body(estimation, "es")
        assert "10 agentes concurrentes" in body

    def test_contains_disclaimer(self):
        """Cuerpo debe contener disclaimer."""
        estimation = _make_estimation()
        body = _build_plain_text_body(estimation, "es")
        assert "aproximados" in body
        assert "sujetos a cambios" in body

    def test_contains_external_estimations_when_consolidated(self):
        """Cuerpo con consolidación debe incluir estimaciones externas."""
        estimation = _make_estimation(
            is_consolidated=True,
            external_estimations={
                "external_services": [
                    {
                        "service_name": "Salesforce",
                        "provider": "Salesforce Inc",
                        "monthly_cost": 500.0,
                        "annual_cost": 6000.0,
                    }
                ]
            },
        )
        body = _build_plain_text_body(estimation, "es")
        assert "ESTIMACIONES EXTERNAS" in body
        assert "Salesforce" in body
        assert "TOTAL CONSOLIDADO" in body

    def test_no_external_section_when_not_consolidated(self):
        """Cuerpo sin consolidación no debe tener sección de externos."""
        estimation = _make_estimation()
        body = _build_plain_text_body(estimation, "es")
        assert "ESTIMACIONES EXTERNAS" not in body
        assert "TOTAL CONSOLIDADO" not in body

    def test_contains_pricing_date(self):
        """Cuerpo debe contener fecha de precios."""
        estimation = _make_estimation()
        body = _build_plain_text_body(estimation, "es")
        assert "2024-01-15" in body


class TestSendEstimationEmail:
    """Tests para send_estimation_email."""

    @mock_aws
    def test_send_email_success(self):
        """Envío exitoso retorna message_id y status sent."""
        ses = boto3.client("ses", region_name="us-east-1")
        ses.verify_email_identity(EmailAddress="noreply@preventa.example.com")

        estimation = _make_estimation()
        pdf_bytes = b"%PDF-1.4 fake pdf content"

        result = send_estimation_email(
            ses, estimation, "recipient@example.com", pdf_bytes, "es"
        )
        assert result["status"] == "sent"
        assert result["message_id"] != ""

    @mock_aws
    def test_send_email_returns_dict(self):
        """Resultado debe ser un diccionario con message_id y status."""
        ses = boto3.client("ses", region_name="us-east-1")
        ses.verify_email_identity(EmailAddress="noreply@preventa.example.com")

        estimation = _make_estimation()
        result = send_estimation_email(
            ses, estimation, "recipient@example.com", b"pdf", "es"
        )
        assert "message_id" in result
        assert "status" in result
