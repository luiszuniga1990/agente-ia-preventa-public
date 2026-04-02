"""Tests unitarios para el servicio de consolidación."""

import pytest

from src.models.estimation import Estimation
from src.models.partner import PartnerData
from src.services import consolidation_service, estimation_repo


def _save_base_estimation(dynamodb) -> str:
    """Guardar estimación base para consolidación."""
    estimation = Estimation(
        estimation_id="est-base-001",
        conversation_id="conv-001",
        user_id="user-001",
        service="amazon_connect",
        partner_data=PartnerData(
            partner_name="Acme Corp",
            partner_email="acme@example.com",
            region="LATAM",
            end_customer="Cliente SA",
        ),
        monthly_cost=1000.0,
        annual_cost=12000.0,
        breakdown=[
            {"component": "License", "unit_price": 100.0, "quantity": 10, "monthly_cost": 1000.0}
        ],
        assumptions=["10 agentes"],
        pricing_date="2024-01-15T00:00:00+00:00",
        created_at="2024-01-20T10:00:00+00:00",
    )
    estimation_repo.save_estimation(dynamodb, estimation)
    return estimation.estimation_id


class TestConsolidate:
    """Tests para consolidation_service.consolidate."""

    def test_consolidate_success(self, dynamodb_resource):
        """Consolidación exitosa crea nueva estimación con datos externos."""
        est_id = _save_base_estimation(dynamodb_resource)
        external = {
            "external_services": [
                {
                    "service_name": "Salesforce",
                    "provider": "Salesforce Inc",
                    "monthly_cost": 500.0,
                    "annual_cost": 6000.0,
                }
            ]
        }
        result = consolidation_service.consolidate(
            dynamodb_resource, est_id, external
        )
        assert result.is_consolidated is True
        assert result.external_estimations == external
        assert result.monthly_cost == 1500.0
        assert result.annual_cost == 18000.0
        assert result.estimation_id != est_id

    def test_consolidate_preserves_partner_data(self, dynamodb_resource):
        """Consolidación preserva datos del partner de la estimación original."""
        est_id = _save_base_estimation(dynamodb_resource)
        external = {"external_services": []}
        result = consolidation_service.consolidate(
            dynamodb_resource, est_id, external
        )
        assert result.partner_data.partner_name == "Acme Corp"
        assert result.partner_data.partner_email == "acme@example.com"

    def test_consolidate_estimation_not_found(self, dynamodb_resource):
        """Estimación no encontrada lanza ValueError."""
        with pytest.raises(ValueError, match="no encontrada"):
            consolidation_service.consolidate(
                dynamodb_resource, "nonexistent", {"external_services": []}
            )

    def test_consolidate_external_data_unmodified(self, dynamodb_resource):
        """Datos externos se preservan sin modificación."""
        est_id = _save_base_estimation(dynamodb_resource)
        external = {
            "external_services": [
                {
                    "service_name": "Custom SaaS",
                    "provider": "Vendor X",
                    "monthly_cost": 250.75,
                    "annual_cost": 3009.0,
                    "notes": "Incluye soporte premium",
                }
            ]
        }
        result = consolidation_service.consolidate(
            dynamodb_resource, est_id, external
        )
        stored_ext = result.external_estimations["external_services"][0]
        assert stored_ext["service_name"] == "Custom SaaS"
        assert stored_ext["monthly_cost"] == 250.75
        assert stored_ext["notes"] == "Incluye soporte premium"

    def test_consolidate_multiple_external_services(self, dynamodb_resource):
        """Consolidación con múltiples servicios externos suma correctamente."""
        est_id = _save_base_estimation(dynamodb_resource)
        external = {
            "external_services": [
                {"service_name": "SvcA", "provider": "A", "monthly_cost": 200.0, "annual_cost": 2400.0},
                {"service_name": "SvcB", "provider": "B", "monthly_cost": 300.0, "annual_cost": 3600.0},
            ]
        }
        result = consolidation_service.consolidate(
            dynamodb_resource, est_id, external
        )
        assert result.monthly_cost == 1500.0  # 1000 + 200 + 300
        assert result.annual_cost == 18000.0  # 12000 + 2400 + 3600

    def test_consolidate_saves_to_dynamodb(self, dynamodb_resource):
        """Estimación consolidada se guarda en DynamoDB."""
        est_id = _save_base_estimation(dynamodb_resource)
        external = {"external_services": []}
        result = consolidation_service.consolidate(
            dynamodb_resource, est_id, external
        )
        # Verificar que se puede recuperar
        stored = estimation_repo.get_estimation(dynamodb_resource, result.estimation_id)
        assert stored is not None
        assert stored.is_consolidated is True
