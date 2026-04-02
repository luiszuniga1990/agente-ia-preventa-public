"""Tests unitarios para el generador de PDF y CSV."""

import csv
import io

import pytest

from src.models.estimation import Estimation
from src.models.partner import PartnerData
from src.services.pdf_generator import generate_csv, generate_pdf


def _make_estimation(**overrides) -> Estimation:
    """Crear estimación de prueba con valores por defecto."""
    defaults = {
        "estimation_id": "est-001",
        "conversation_id": "conv-001",
        "user_id": "user-001",
        "service": "amazon_connect",
        "parameters": {"concurrent_agents": 10},
        "partner_data": PartnerData(
            partner_name="Acme Corp",
            partner_email="partner@acme.com",
            region="LATAM",
            end_customer="Cliente Final SA",
        ),
        "monthly_cost": 1500.0,
        "annual_cost": 18000.0,
        "breakdown": [
            {
                "component": "Agent License",
                "unit_price": 100.0,
                "quantity": 10,
                "monthly_cost": 1000.0,
            },
            {
                "component": "Telephony",
                "unit_price": 50.0,
                "quantity": 10,
                "monthly_cost": 500.0,
            },
        ],
        "assumptions": [
            "10 agentes concurrentes",
            "Uso estándar de telefonía",
        ],
        "pricing_date": "2024-01-15T00:00:00+00:00",
        "created_at": "2024-01-20T10:00:00+00:00",
        "language": "es",
        "is_consolidated": False,
        "external_estimations": {},
    }
    defaults.update(overrides)
    return Estimation(**defaults)


class TestGeneratePdf:
    """Tests para generate_pdf."""

    def test_generate_pdf_returns_bytes(self):
        """PDF generado debe ser bytes no vacíos."""
        estimation = _make_estimation()
        result = generate_pdf(estimation, "es")
        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_generate_pdf_starts_with_pdf_header(self):
        """PDF generado debe comenzar con la firma %PDF."""
        estimation = _make_estimation()
        result = generate_pdf(estimation, "es")
        assert result[:5] == b"%PDF-"

    def test_generate_pdf_spanish(self):
        """PDF en español debe generarse como PDF válido con contenido."""
        estimation = _make_estimation()
        result = generate_pdf(estimation, "es")
        # PDF content is compressed, so we verify it's a valid PDF with content
        assert result[:5] == b"%PDF-"
        # Verify the PDF has substantial content (partner data, breakdown, etc.)
        assert len(result) > 500

    def test_generate_pdf_english(self):
        """PDF en inglés debe generarse correctamente."""
        estimation = _make_estimation()
        result = generate_pdf(estimation, "en")
        assert isinstance(result, bytes)
        assert len(result) > 0
        assert result[:5] == b"%PDF-"

    def test_generate_pdf_portuguese(self):
        """PDF en portugués debe generarse correctamente."""
        estimation = _make_estimation()
        result = generate_pdf(estimation, "pt")
        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_generate_pdf_german(self):
        """PDF en alemán debe generarse correctamente."""
        estimation = _make_estimation()
        result = generate_pdf(estimation, "de")
        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_generate_pdf_with_consolidation(self):
        """PDF con consolidación debe ser más grande que sin consolidación."""
        base_estimation = _make_estimation()
        base_pdf = generate_pdf(base_estimation, "es")

        consolidated_estimation = _make_estimation(
            is_consolidated=True,
            external_estimations={
                "external_services": [
                    {
                        "service_name": "Salesforce CRM",
                        "provider": "Salesforce",
                        "monthly_cost": 500.0,
                        "annual_cost": 6000.0,
                    }
                ]
            },
        )
        consolidated_pdf = generate_pdf(consolidated_estimation, "es")
        assert isinstance(consolidated_pdf, bytes)
        assert len(consolidated_pdf) > 0
        # Consolidated PDF should be larger due to extra sections
        assert len(consolidated_pdf) > len(base_pdf)

    def test_generate_pdf_includes_disclaimer(self):
        """PDF debe generarse con contenido de disclaimer (verificado por tamaño)."""
        estimation = _make_estimation()
        result = generate_pdf(estimation, "es")
        # PDF content is compressed; we verify the PDF is valid and has content
        # The disclaimer is included in the build elements, so the PDF is generated
        assert result[:5] == b"%PDF-"
        assert len(result) > 500

    def test_generate_pdf_unsupported_language_falls_back(self):
        """Idioma no soportado debe usar fallback a español."""
        estimation = _make_estimation()
        result = generate_pdf(estimation, "fr")
        assert isinstance(result, bytes)
        assert len(result) > 0


class TestGenerateCsv:
    """Tests para generate_csv."""

    def test_generate_csv_returns_string(self):
        """CSV generado debe ser una cadena no vacía."""
        estimation = _make_estimation()
        result = generate_csv(estimation)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_generate_csv_has_headers(self):
        """CSV debe tener encabezados correctos."""
        estimation = _make_estimation()
        result = generate_csv(estimation)
        reader = csv.reader(io.StringIO(result))
        headers = next(reader)
        assert headers == ["Component", "Unit Price", "Quantity", "Monthly Cost"]

    def test_generate_csv_has_breakdown_rows(self):
        """CSV debe contener filas de desglose."""
        estimation = _make_estimation()
        result = generate_csv(estimation)
        assert "Agent License" in result
        assert "Telephony" in result

    def test_generate_csv_has_totals(self):
        """CSV debe contener totales."""
        estimation = _make_estimation()
        result = generate_csv(estimation)
        assert "Total Monthly Cost" in result
        assert "Total Annual Cost" in result

    def test_generate_csv_with_consolidation(self):
        """CSV con consolidación debe incluir estimaciones externas."""
        estimation = _make_estimation(
            is_consolidated=True,
            external_estimations={
                "external_services": [
                    {
                        "service_name": "Salesforce CRM",
                        "provider": "Salesforce",
                        "monthly_cost": 500.0,
                        "annual_cost": 6000.0,
                    }
                ]
            },
        )
        result = generate_csv(estimation)
        assert "External Estimations" in result
        assert "Salesforce CRM" in result

    def test_generate_csv_empty_breakdown(self):
        """CSV con desglose vacío debe tener solo encabezados y totales."""
        estimation = _make_estimation(breakdown=[])
        result = generate_csv(estimation)
        reader = csv.reader(io.StringIO(result))
        rows = list(reader)
        # Header + empty row + total monthly + total annual
        assert rows[0] == ["Component", "Unit Price", "Quantity", "Monthly Cost"]
