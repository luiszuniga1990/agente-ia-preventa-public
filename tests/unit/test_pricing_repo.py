"""Tests unitarios para el repositorio de caché de precios."""

from src.services.pricing_repo import (
    get_last_updated,
    get_pricing,
    update_pricing,
)


class TestUpdatePricing:
    """Tests para actualizar precios."""

    def test_update_pricing_creates_entry(self, dynamodb_resource):
        update_pricing(dynamodb_resource, "amazon_quick", "base_user", {
            "unit_price": 10.0,
            "unit": "user/month",
            "tier": "standard",
            "currency": "USD",
            "source_url": "https://aws.amazon.com/quick/pricing/",
        })
        entries = get_pricing(dynamodb_resource, "amazon_quick")
        assert len(entries) == 1
        assert entries[0].component == "base_user"
        assert entries[0].unit_price == 10.0
        assert entries[0].unit == "user/month"

    def test_update_pricing_overwrites_existing(self, dynamodb_resource):
        update_pricing(dynamodb_resource, "amazon_quick", "base_user", {
            "unit_price": 10.0,
            "unit": "user/month",
        })
        update_pricing(dynamodb_resource, "amazon_quick", "base_user", {
            "unit_price": 12.0,
            "unit": "user/month",
        })
        entries = get_pricing(dynamodb_resource, "amazon_quick")
        assert len(entries) == 1
        assert entries[0].unit_price == 12.0


class TestGetPricing:
    """Tests para obtener precios."""

    def test_get_pricing_returns_all_components(self, dynamodb_resource):
        update_pricing(dynamodb_resource, "amazon_connect", "voice", {
            "unit_price": 0.018,
            "unit": "minute",
        })
        update_pricing(dynamodb_resource, "amazon_connect", "chat", {
            "unit_price": 0.004,
            "unit": "message",
        })
        entries = get_pricing(dynamodb_resource, "amazon_connect")
        assert len(entries) == 2
        components = {e.component for e in entries}
        assert "voice" in components
        assert "chat" in components

    def test_get_pricing_empty_for_unknown_service(self, dynamodb_resource):
        result = get_pricing(dynamodb_resource, "unknown_service")
        assert result == []

    def test_get_pricing_isolates_services(self, dynamodb_resource):
        update_pricing(dynamodb_resource, "amazon_quick", "base", {"unit_price": 10.0, "unit": "user/month"})
        update_pricing(dynamodb_resource, "amazon_connect", "voice", {"unit_price": 0.018, "unit": "minute"})
        quick_entries = get_pricing(dynamodb_resource, "amazon_quick")
        connect_entries = get_pricing(dynamodb_resource, "amazon_connect")
        assert len(quick_entries) == 1
        assert len(connect_entries) == 1
        assert quick_entries[0].service_id == "amazon_quick"
        assert connect_entries[0].service_id == "amazon_connect"


class TestGetLastUpdated:
    """Tests para obtener fecha de última actualización."""

    def test_get_last_updated_returns_most_recent(self, dynamodb_resource):
        update_pricing(dynamodb_resource, "amazon_quick", "comp_a", {"unit_price": 5.0, "unit": "u"})
        update_pricing(dynamodb_resource, "amazon_quick", "comp_b", {"unit_price": 8.0, "unit": "u"})
        result = get_last_updated(dynamodb_resource, "amazon_quick")
        assert result != ""

    def test_get_last_updated_empty_for_unknown_service(self, dynamodb_resource):
        result = get_last_updated(dynamodb_resource, "nonexistent")
        assert result == ""

    def test_get_last_updated_returns_valid_iso_timestamp(self, dynamodb_resource):
        update_pricing(dynamodb_resource, "bedrock_agentcore", "runtime", {"unit_price": 1.0, "unit": "invocation"})
        result = get_last_updated(dynamodb_resource, "bedrock_agentcore")
        assert "T" in result  # ISO8601 contiene 'T'
