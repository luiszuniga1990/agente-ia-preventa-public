"""Tests unitarios para los modelos de datos."""

import uuid
from datetime import datetime

from src.models import (
    CONVERSATION_STATUSES,
    DEFAULT_CURRENCY,
    SUPPORTED_LANGUAGES,
    SUPPORTED_SERVICES,
    Conversation,
    Estimation,
    PartnerData,
    PricingEntry,
)


class TestConstants:
    """Tests para las constantes del sistema."""

    def test_supported_services_contains_three_services(self):
        assert len(SUPPORTED_SERVICES) == 3
        assert "amazon_quick" in SUPPORTED_SERVICES
        assert "amazon_connect" in SUPPORTED_SERVICES
        assert "bedrock_agentcore" in SUPPORTED_SERVICES

    def test_supported_languages_contains_four_languages(self):
        assert len(SUPPORTED_LANGUAGES) == 4
        assert "es" in SUPPORTED_LANGUAGES
        assert "en" in SUPPORTED_LANGUAGES
        assert "pt" in SUPPORTED_LANGUAGES
        assert "de" in SUPPORTED_LANGUAGES

    def test_conversation_statuses(self):
        assert "active" in CONVERSATION_STATUSES
        assert "completed" in CONVERSATION_STATUSES

    def test_default_currency_is_usd(self):
        assert DEFAULT_CURRENCY == "USD"


class TestPartnerData:
    """Tests para el modelo PartnerData."""

    def test_default_values(self):
        partner = PartnerData()
        assert partner.partner_name == ""
        assert partner.partner_email == ""
        assert partner.region == ""
        assert partner.end_customer == ""

    def test_custom_values(self):
        partner = PartnerData(
            partner_name="Acme Corp",
            partner_email="contact@acme.com",
            region="LATAM",
            end_customer="Cliente Final SA",
        )
        assert partner.partner_name == "Acme Corp"
        assert partner.partner_email == "contact@acme.com"
        assert partner.region == "LATAM"
        assert partner.end_customer == "Cliente Final SA"


class TestPricingEntry:
    """Tests para el modelo PricingEntry."""

    def test_default_values(self):
        entry = PricingEntry()
        assert entry.service_id == ""
        assert entry.component == ""
        assert entry.unit_price == 0.0
        assert entry.unit == ""
        assert entry.last_updated == ""

    def test_custom_values(self):
        entry = PricingEntry(
            service_id="amazon_connect",
            component="voice_usage",
            unit_price=0.018,
            unit="minute",
            last_updated="2024-01-15T10:00:00+00:00",
        )
        assert entry.service_id == "amazon_connect"
        assert entry.unit_price == 0.018
        assert entry.unit == "minute"


class TestConversation:
    """Tests para el modelo Conversation."""

    def test_default_values_generate_uuid_and_timestamps(self):
        conv = Conversation()
        # conversation_id debe ser un UUID válido
        uuid.UUID(conv.conversation_id)
        # created_at y updated_at deben ser ISO8601 parseables
        datetime.fromisoformat(conv.created_at)
        datetime.fromisoformat(conv.updated_at)
        assert conv.user_id == ""
        assert conv.messages == []
        assert conv.language == "es"
        assert conv.status == "active"

    def test_custom_values(self):
        messages = [
            {"role": "user", "content": "Hola", "timestamp": "2024-01-01T00:00:00Z"}
        ]
        conv = Conversation(
            conversation_id="test-id",
            user_id="user-123",
            messages=messages,
            language="en",
            status="completed",
        )
        assert conv.conversation_id == "test-id"
        assert conv.user_id == "user-123"
        assert len(conv.messages) == 1
        assert conv.messages[0]["role"] == "user"
        assert conv.language == "en"
        assert conv.status == "completed"

    def test_two_conversations_have_different_ids(self):
        conv1 = Conversation()
        conv2 = Conversation()
        assert conv1.conversation_id != conv2.conversation_id


class TestEstimation:
    """Tests para el modelo Estimation."""

    def test_default_values(self):
        est = Estimation()
        uuid.UUID(est.estimation_id)
        datetime.fromisoformat(est.created_at)
        assert est.conversation_id == ""
        assert est.user_id == ""
        assert est.service == ""
        assert est.parameters == {}
        assert isinstance(est.partner_data, PartnerData)
        assert est.monthly_cost == 0.0
        assert est.annual_cost == 0.0
        assert est.breakdown == []
        assert est.assumptions == []
        assert est.pricing_date == ""
        assert est.language == "es"
        assert est.is_consolidated is False
        assert est.external_estimations == {}
        assert est.pdf_s3_key == ""

    def test_custom_values_with_partner_data(self):
        partner = PartnerData(
            partner_name="Test Partner",
            partner_email="test@partner.com",
            region="US",
            end_customer="End Customer Inc",
        )
        breakdown = [
            {
                "component": "Base",
                "unit_price": 10.0,
                "quantity": 5,
                "monthly_cost": 50.0,
            }
        ]
        est = Estimation(
            service="amazon_quick",
            partner_data=partner,
            monthly_cost=50.0,
            annual_cost=600.0,
            breakdown=breakdown,
            assumptions=["5 usuarios activos"],
            pricing_date="2024-01-15T00:00:00+00:00",
        )
        assert est.service == "amazon_quick"
        assert est.partner_data.partner_name == "Test Partner"
        assert est.monthly_cost == 50.0
        assert est.annual_cost == 600.0
        assert len(est.breakdown) == 1
        assert est.breakdown[0]["component"] == "Base"
        assert len(est.assumptions) == 1

    def test_two_estimations_have_different_ids(self):
        est1 = Estimation()
        est2 = Estimation()
        assert est1.estimation_id != est2.estimation_id

    def test_consolidated_estimation(self):
        est = Estimation(
            is_consolidated=True,
            external_estimations={
                "external_services": [
                    {"service_name": "Salesforce", "monthly_cost": 100.0}
                ]
            },
        )
        assert est.is_consolidated is True
        assert len(est.external_estimations["external_services"]) == 1
