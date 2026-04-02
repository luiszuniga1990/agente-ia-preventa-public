"""Tests unitarios para el scraper de precios."""

from unittest.mock import MagicMock, patch

import pytest

from src.services.pricing_scraper import (
    PRICING_URLS,
    _extract_from_tables,
    _extract_pricing_from_html,
    _get_parser,
    fetch_pricing,
)


class TestFetchPricing:
    """Tests para la función principal fetch_pricing."""

    @patch("src.services.pricing_scraper._fetch_html")
    def test_fetch_pricing_returns_parsed_data(self, mock_fetch):
        """fetch_pricing retorna datos parseados del HTML."""
        mock_fetch.return_value = '<p>$10.00 per user/month</p>'
        result = fetch_pricing("amazon_quick", "https://example.com")
        assert len(result) >= 1
        assert result[0]["unit_price"] == 10.0
        assert result[0]["currency"] == "USD"
        assert result[0]["source_url"] == "https://example.com"

    @patch("src.services.pricing_scraper._fetch_html")
    def test_fetch_pricing_connection_error(self, mock_fetch):
        """fetch_pricing propaga ConnectionError de _fetch_html."""
        mock_fetch.side_effect = ConnectionError("Timeout")
        with pytest.raises(ConnectionError):
            fetch_pricing("amazon_quick", "https://example.com")

    @patch("src.services.pricing_scraper._fetch_html")
    def test_fetch_pricing_invalid_service(self, mock_fetch):
        """fetch_pricing lanza ValueError para servicio sin parser."""
        mock_fetch.return_value = "<html></html>"
        with pytest.raises(ValueError, match="No hay parser"):
            fetch_pricing("servicio_invalido", "https://example.com")


class TestGetParser:
    """Tests para obtención de parsers por servicio."""

    def test_get_parser_amazon_quick(self):
        parser = _get_parser("amazon_quick")
        assert callable(parser)

    def test_get_parser_amazon_connect(self):
        parser = _get_parser("amazon_connect")
        assert callable(parser)

    def test_get_parser_bedrock_agentcore(self):
        parser = _get_parser("bedrock_agentcore")
        assert callable(parser)

    def test_get_parser_unknown_service(self):
        with pytest.raises(ValueError):
            _get_parser("unknown_service")


class TestExtractPricingFromHtml:
    """Tests para la extracción de precios desde HTML."""

    def test_extracts_price_per_unit(self):
        """Extrae precios con formato $X.XX per unit."""
        html = '<div>$0.50 per minute</div><div>$25.00 per user/month</div>'
        result = _extract_pricing_from_html(html, "https://test.com", "amazon_connect")
        assert len(result) == 2
        prices = {r["unit_price"] for r in result}
        assert 0.50 in prices
        assert 25.0 in prices

    def test_extracts_price_with_comma(self):
        """Extrae precios con comas en miles."""
        html = '<p>$1,500.00 per month</p>'
        result = _extract_pricing_from_html(html, "https://test.com", "amazon_quick")
        assert len(result) == 1
        assert result[0]["unit_price"] == 1500.0

    def test_empty_html_returns_empty(self):
        """HTML vacío retorna lista vacía."""
        result = _extract_pricing_from_html("", "https://test.com", "amazon_quick")
        assert result == []

    def test_no_prices_in_html(self):
        """HTML sin precios retorna lista vacía."""
        html = "<html><body>No pricing info here</body></html>"
        result = _extract_pricing_from_html(html, "https://test.com", "amazon_quick")
        assert result == []

    def test_deduplicates_prices(self):
        """No duplica precios idénticos."""
        html = '<p>$10.00 per user</p><p>$10.00 per user</p>'
        result = _extract_pricing_from_html(html, "https://test.com", "amazon_quick")
        assert len(result) == 1

    def test_result_structure(self):
        """Cada resultado tiene las claves requeridas."""
        html = '<p>$5.00 per invocation</p>'
        result = _extract_pricing_from_html(
            html, "https://test.com", "bedrock_agentcore"
        )
        assert len(result) == 1
        entry = result[0]
        assert "unit_price" in entry
        assert "unit" in entry
        assert "tier" in entry
        assert "currency" in entry
        assert "source_url" in entry
        assert "raw_data" in entry


class TestExtractFromTables:
    """Tests para extracción de precios desde tablas HTML."""

    def test_extracts_from_td_elements(self):
        """Extrae precios de celdas <td>."""
        html = '<table><tr><td>$12.50</td><td>Basic</td></tr></table>'
        result = _extract_from_tables(html, "https://test.com", "amazon_quick")
        assert len(result) == 1
        assert result[0]["unit_price"] == 12.5

    def test_no_tables_returns_empty(self):
        """Sin tablas retorna lista vacía."""
        html = "<p>No tables here</p>"
        result = _extract_from_tables(html, "https://test.com", "amazon_quick")
        assert result == []


class TestPricingUrls:
    """Tests para las URLs de pricing configuradas."""

    def test_all_services_have_urls(self):
        """Todos los servicios soportados tienen URL de pricing."""
        assert "amazon_quick" in PRICING_URLS
        assert "amazon_connect" in PRICING_URLS
        assert "bedrock_agentcore" in PRICING_URLS

    def test_urls_are_https(self):
        """Todas las URLs usan HTTPS."""
        for url in PRICING_URLS.values():
            assert url.startswith("https://")
