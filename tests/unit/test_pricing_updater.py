"""Tests unitarios para el handler de actualización de precios."""

from unittest.mock import MagicMock, patch

from src.handlers.pricing_updater import handler


class TestPricingUpdaterHandler:
    """Tests para el handler de pricing_updater."""

    @patch("src.handlers.pricing_updater.fetch_pricing")
    @patch("src.handlers.pricing_updater.pricing_repo")
    @patch("src.handlers.pricing_updater.boto3")
    def test_successful_update_all_services(
        self, mock_boto3, mock_repo, mock_fetch
    ):
        """Actualización exitosa de todos los servicios."""
        mock_dynamodb = MagicMock()
        mock_boto3.resource.return_value = mock_dynamodb

        mock_fetch.return_value = [
            {
                "unit_price": 10.0,
                "unit": "user/month",
                "tier": "standard",
                "currency": "USD",
                "source_url": "https://example.com",
                "raw_data": {},
            }
        ]

        result = handler({"source": "aws.events"}, None)

        assert len(result["services_updated"]) == 3
        assert result["total_errors"] == 0
        assert "timestamp" in result

    @patch("src.handlers.pricing_updater.fetch_pricing")
    @patch("src.handlers.pricing_updater.pricing_repo")
    @patch("src.handlers.pricing_updater.boto3")
    def test_partial_failure_keeps_cache(
        self, mock_boto3, mock_repo, mock_fetch
    ):
        """Si un servicio falla, los demás se actualizan normalmente."""
        mock_dynamodb = MagicMock()
        mock_boto3.resource.return_value = mock_dynamodb

        call_count = 0

        def side_effect(service_id, url):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ConnectionError("Timeout")
            return [{"unit_price": 5.0, "unit": "minute", "tier": "standard",
                      "currency": "USD", "source_url": url, "raw_data": {}}]

        mock_fetch.side_effect = side_effect

        result = handler({"source": "aws.events"}, None)

        assert len(result["services_updated"]) == 2
        assert len(result["errors"]) == 1

    @patch("src.handlers.pricing_updater.fetch_pricing")
    @patch("src.handlers.pricing_updater.pricing_repo")
    @patch("src.handlers.pricing_updater.boto3")
    def test_all_urls_fail_logs_critical(
        self, mock_boto3, mock_repo, mock_fetch
    ):
        """Si todas las URLs fallan, mantiene caché y registra error crítico."""
        mock_dynamodb = MagicMock()
        mock_boto3.resource.return_value = mock_dynamodb
        mock_fetch.side_effect = ConnectionError("Network error")

        result = handler({"source": "aws.events"}, None)

        assert result["services_updated"] == []
        assert len(result["errors"]) == 3
        assert result["total_updated"] == 0

    @patch("src.handlers.pricing_updater.fetch_pricing")
    @patch("src.handlers.pricing_updater.pricing_repo")
    @patch("src.handlers.pricing_updater.boto3")
    def test_empty_pricing_data_recorded_as_error(
        self, mock_boto3, mock_repo, mock_fetch
    ):
        """Si fetch retorna lista vacía, se registra como error."""
        mock_dynamodb = MagicMock()
        mock_boto3.resource.return_value = mock_dynamodb
        mock_fetch.return_value = []

        result = handler({"source": "aws.events"}, None)

        assert result["services_updated"] == []
        assert len(result["errors"]) == 3

    @patch("src.handlers.pricing_updater.fetch_pricing")
    @patch("src.handlers.pricing_updater.pricing_repo")
    @patch("src.handlers.pricing_updater.boto3")
    def test_updates_pricing_repo_for_each_component(
        self, mock_boto3, mock_repo, mock_fetch
    ):
        """Actualiza pricing_repo para cada componente obtenido."""
        mock_dynamodb = MagicMock()
        mock_boto3.resource.return_value = mock_dynamodb

        mock_fetch.return_value = [
            {"unit_price": 10.0, "unit": "user/month", "tier": "standard",
             "currency": "USD", "source_url": "https://test.com", "raw_data": {}},
            {"unit_price": 5.0, "unit": "minute", "tier": "standard",
             "currency": "USD", "source_url": "https://test.com", "raw_data": {}},
        ]

        handler({"source": "aws.events"}, None)

        # 3 servicios × 2 componentes = 6 llamadas
        assert mock_repo.update_pricing.call_count == 6

    @patch("src.handlers.pricing_updater.fetch_pricing")
    @patch("src.handlers.pricing_updater.pricing_repo")
    @patch("src.handlers.pricing_updater.boto3")
    def test_value_error_handled_gracefully(
        self, mock_boto3, mock_repo, mock_fetch
    ):
        """ValueError del parser se maneja sin crash."""
        mock_dynamodb = MagicMock()
        mock_boto3.resource.return_value = mock_dynamodb
        mock_fetch.side_effect = ValueError("Parse error")

        result = handler({"source": "aws.events"}, None)

        assert result["services_updated"] == []
        assert len(result["errors"]) == 3
