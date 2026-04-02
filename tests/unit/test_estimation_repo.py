"""Tests unitarios para el repositorio de estimaciones."""

from src.models import Estimation, PartnerData
from src.services.estimation_repo import (
    get_estimation,
    list_estimations,
    save_estimation,
)


def _make_estimation(user_id: str = "user-1", service: str = "amazon_quick") -> Estimation:
    """Helper para crear una estimación de prueba."""
    return Estimation(
        conversation_id="conv-1",
        user_id=user_id,
        service=service,
        parameters={"num_users": 10},
        partner_data=PartnerData(
            partner_name="Acme",
            partner_email="acme@test.com",
            region="LATAM",
            end_customer="Cliente SA",
        ),
        monthly_cost=150.0,
        annual_cost=1800.0,
        breakdown=[{"component": "Base", "unit_price": 15.0, "quantity": 10, "monthly_cost": 150.0}],
        assumptions=["10 usuarios activos"],
        pricing_date="2024-01-15T00:00:00+00:00",
        language="es",
    )


class TestSaveEstimation:
    """Tests para guardar estimaciones."""

    def test_save_estimation_returns_id(self, dynamodb_resource):
        est = _make_estimation()
        result_id = save_estimation(dynamodb_resource, est)
        assert result_id == est.estimation_id

    def test_save_estimation_persists_in_dynamodb(self, dynamodb_resource):
        est = _make_estimation()
        save_estimation(dynamodb_resource, est)
        retrieved = get_estimation(dynamodb_resource, est.estimation_id)
        assert retrieved is not None
        assert retrieved.estimation_id == est.estimation_id
        assert retrieved.service == "amazon_quick"
        assert retrieved.monthly_cost == 150.0
        assert retrieved.annual_cost == 1800.0


class TestGetEstimation:
    """Tests para obtener estimaciones."""

    def test_get_existing_estimation(self, dynamodb_resource):
        est = _make_estimation()
        save_estimation(dynamodb_resource, est)
        result = get_estimation(dynamodb_resource, est.estimation_id)
        assert result is not None
        assert result.user_id == "user-1"
        assert result.partner_data.partner_name == "Acme"
        assert result.partner_data.partner_email == "acme@test.com"
        assert len(result.breakdown) == 1
        assert len(result.assumptions) == 1

    def test_get_nonexistent_estimation_returns_none(self, dynamodb_resource):
        result = get_estimation(dynamodb_resource, "nonexistent-id")
        assert result is None

    def test_get_estimation_preserves_partner_data(self, dynamodb_resource):
        est = _make_estimation()
        save_estimation(dynamodb_resource, est)
        result = get_estimation(dynamodb_resource, est.estimation_id)
        assert result.partner_data.region == "LATAM"
        assert result.partner_data.end_customer == "Cliente SA"

    def test_get_consolidated_estimation(self, dynamodb_resource):
        est = _make_estimation()
        est.is_consolidated = True
        est.external_estimations = {
            "external_services": [{"service_name": "Salesforce", "monthly_cost": 100}]
        }
        save_estimation(dynamodb_resource, est)
        result = get_estimation(dynamodb_resource, est.estimation_id)
        assert result.is_consolidated is True
        assert "external_services" in result.external_estimations


class TestListEstimations:
    """Tests para listar estimaciones."""

    def test_list_estimations_for_user(self, dynamodb_resource):
        est1 = _make_estimation(user_id="user-1", service="amazon_quick")
        est2 = _make_estimation(user_id="user-1", service="amazon_connect")
        est3 = _make_estimation(user_id="user-2", service="amazon_quick")
        save_estimation(dynamodb_resource, est1)
        save_estimation(dynamodb_resource, est2)
        save_estimation(dynamodb_resource, est3)
        result = list_estimations(dynamodb_resource, "user-1")
        assert len(result) == 2
        assert all(e.user_id == "user-1" for e in result)

    def test_list_estimations_empty_for_unknown_user(self, dynamodb_resource):
        result = list_estimations(dynamodb_resource, "unknown-user")
        assert result == []
