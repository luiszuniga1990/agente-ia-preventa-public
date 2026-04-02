"""Tests unitarios para el servicio de estimación (estimation_service).

Verifica orquestación de validaciones, invocación a Bedrock, parsing
de respuestas y persistencia en DynamoDB.
"""

import json
from unittest.mock import MagicMock, patch

import pytest
from moto import mock_aws

from src.models.estimation import Estimation
from src.services.estimation_service import (
    DISCLAIMER,
    _extract_json_block,
    _parse_model_response,
    generate_estimation,
)


# --- Datos de prueba ---

VALID_PARTNER_DATA = {
    "partner_name": "Acme Corp",
    "partner_email": "contact@acme.com",
    "region": "LATAM",
    "end_customer": "Cliente Final SA",
}

VALID_PARAMETERS = {
    "num_users": 50,
    "features": {"knowledge_spaces": True, "analytics_dashboards": True},
}

BEDROCK_JSON_RESPONSE = """Aquí está la estimación para Amazon Quick:

```json
{
    "monthly_cost": 1250.00,
    "annual_cost": 15000.00,
    "breakdown": [
        {
            "component": "User licenses",
            "unit_price": 25.0,
            "quantity": 50,
            "monthly_cost": 1250.0
        }
    ],
    "assumptions": [
        "50 usuarios activos",
        "Licencia estándar por usuario"
    ]
}
```"""

BEDROCK_PLAIN_RESPONSE = "La estimación para 50 usuarios es de $1250/mes."


class TestGenerateEstimation:
    """Tests para la función generate_estimation."""

    @patch("src.services.estimation_service.bedrock_mod.invoke_model")
    def test_generacion_exitosa(self, mock_invoke, dynamodb_resource):
        """Verifica generación completa con datos válidos y respuesta JSON."""
        mock_invoke.return_value = BEDROCK_JSON_RESPONSE

        estimation = generate_estimation(
            dynamodb=dynamodb_resource,
            bedrock=MagicMock(),
            user_id="user-123",
            conversation_id="conv-456",
            service="amazon_quick",
            parameters=VALID_PARAMETERS,
            partner_data=VALID_PARTNER_DATA,
            language="es",
        )

        assert isinstance(estimation, Estimation)
        assert estimation.estimation_id != ""
        assert estimation.user_id == "user-123"
        assert estimation.conversation_id == "conv-456"
        assert estimation.service == "amazon_quick"
        assert estimation.monthly_cost == 1250.00
        assert estimation.annual_cost == 15000.00
        assert len(estimation.breakdown) > 0
        assert estimation.partner_data.partner_name == "Acme Corp"
        assert estimation.partner_data.partner_email == "contact@acme.com"
        assert estimation.language == "es"
        assert estimation.pricing_date != ""

    @patch("src.services.estimation_service.bedrock_mod.invoke_model")
    def test_disclaimer_incluido(self, mock_invoke, dynamodb_resource):
        """Verifica que el disclaimer se incluye en assumptions."""
        mock_invoke.return_value = BEDROCK_JSON_RESPONSE

        estimation = generate_estimation(
            dynamodb=dynamodb_resource,
            bedrock=MagicMock(),
            user_id="user-1",
            conversation_id="conv-1",
            service="amazon_connect",
            parameters={"concurrent_agents": 10},
            partner_data=VALID_PARTNER_DATA,
        )

        disclaimer_found = any(
            "aproximados" in a.lower() or "approximate" in a.lower()
            for a in estimation.assumptions
        )
        assert disclaimer_found, "El disclaimer debe estar en assumptions"

    @patch("src.services.estimation_service.bedrock_mod.invoke_model")
    def test_estimacion_guardada_en_dynamodb(self, mock_invoke, dynamodb_resource):
        """Verifica que la estimación se persiste en DynamoDB."""
        mock_invoke.return_value = BEDROCK_JSON_RESPONSE

        estimation = generate_estimation(
            dynamodb=dynamodb_resource,
            bedrock=MagicMock(),
            user_id="user-1",
            conversation_id="conv-1",
            service="amazon_quick",
            parameters=VALID_PARAMETERS,
            partner_data=VALID_PARTNER_DATA,
        )

        # Verificar que se puede recuperar de DynamoDB
        from src.services.estimation_repo import get_estimation
        saved = get_estimation(dynamodb_resource, estimation.estimation_id)
        assert saved is not None
        assert saved.estimation_id == estimation.estimation_id
        assert saved.service == "amazon_quick"

    def test_servicio_no_soportado(self, dynamodb_resource):
        """Verifica ValueError para servicio no soportado."""
        with pytest.raises(ValueError, match="Servicio no soportado"):
            generate_estimation(
                dynamodb=dynamodb_resource,
                bedrock=MagicMock(),
                user_id="user-1",
                conversation_id="conv-1",
                service="amazon_s3",
                parameters={},
                partner_data=VALID_PARTNER_DATA,
            )

    def test_partner_data_incompleto(self, dynamodb_resource):
        """Verifica ValueError cuando faltan campos del partner."""
        incomplete_partner = {
            "partner_name": "Acme",
            "partner_email": "a@b.com",
            # Falta region y end_customer
        }

        with pytest.raises(ValueError, match="Campos faltantes"):
            generate_estimation(
                dynamodb=dynamodb_resource,
                bedrock=MagicMock(),
                user_id="user-1",
                conversation_id="conv-1",
                service="amazon_quick",
                parameters={},
                partner_data=incomplete_partner,
            )

    def test_email_invalido(self, dynamodb_resource):
        """Verifica ValueError para email con formato inválido."""
        bad_email_partner = {
            "partner_name": "Acme",
            "partner_email": "not-an-email",
            "region": "LATAM",
            "end_customer": "Cliente",
        }

        with pytest.raises(ValueError, match="correo electrónico inválido"):
            generate_estimation(
                dynamodb=dynamodb_resource,
                bedrock=MagicMock(),
                user_id="user-1",
                conversation_id="conv-1",
                service="amazon_quick",
                parameters={},
                partner_data=bad_email_partner,
            )

    @patch("src.services.estimation_service.bedrock_mod.invoke_model")
    def test_fallback_respuesta_sin_json(self, mock_invoke, dynamodb_resource):
        """Verifica fallback cuando Bedrock no devuelve JSON."""
        mock_invoke.return_value = BEDROCK_PLAIN_RESPONSE

        estimation = generate_estimation(
            dynamodb=dynamodb_resource,
            bedrock=MagicMock(),
            user_id="user-1",
            conversation_id="conv-1",
            service="amazon_quick",
            parameters=VALID_PARAMETERS,
            partner_data=VALID_PARTNER_DATA,
        )

        assert isinstance(estimation, Estimation)
        assert estimation.monthly_cost == 0.0
        assert len(estimation.breakdown) > 0
        assert len(estimation.assumptions) > 0

    @patch("src.services.estimation_service.bedrock_mod.invoke_model")
    def test_bedrock_error_propagado(self, mock_invoke, dynamodb_resource):
        """Verifica que RuntimeError de Bedrock se propaga."""
        mock_invoke.side_effect = RuntimeError(
            "El servicio está temporalmente fuera de servicio."
        )

        with pytest.raises(RuntimeError, match="temporalmente fuera de servicio"):
            generate_estimation(
                dynamodb=dynamodb_resource,
                bedrock=MagicMock(),
                user_id="user-1",
                conversation_id="conv-1",
                service="amazon_quick",
                parameters=VALID_PARAMETERS,
                partner_data=VALID_PARTNER_DATA,
            )


class TestParseModelResponse:
    """Tests para _parse_model_response."""

    def test_parseo_json_valido(self):
        """Verifica extracción correcta de JSON embebido."""
        monthly, annual, breakdown, assumptions = _parse_model_response(
            BEDROCK_JSON_RESPONSE
        )
        assert monthly == 1250.00
        assert annual == 15000.00
        assert len(breakdown) == 1
        assert breakdown[0]["component"] == "User licenses"
        assert len(assumptions) >= 1

    def test_fallback_sin_json(self):
        """Verifica fallback con respuesta sin JSON."""
        monthly, annual, breakdown, assumptions = _parse_model_response(
            "Solo texto sin JSON."
        )
        assert monthly == 0.0
        assert annual == 0.0
        assert len(breakdown) > 0
        assert len(assumptions) > 0

    def test_respuesta_vacia(self):
        """Verifica manejo de respuesta vacía."""
        monthly, annual, breakdown, assumptions = _parse_model_response("")
        assert monthly == 0.0
        assert annual == 0.0

    def test_json_puro(self):
        """Verifica parsing de respuesta que es solo JSON."""
        pure_json = json.dumps({
            "monthly_cost": 500,
            "annual_cost": 6000,
            "breakdown": [
                {"component": "Base", "unit_price": 500, "quantity": 1, "monthly_cost": 500}
            ],
            "assumptions": ["Uso estándar"],
        })
        monthly, annual, breakdown, assumptions = _parse_model_response(pure_json)
        assert monthly == 500.0
        assert annual == 6000.0


class TestExtractJsonBlock:
    """Tests para _extract_json_block."""

    def test_bloque_json_delimitado(self):
        """Verifica extracción de bloque ```json ... ```."""
        text = 'Texto previo\n```json\n{"key": "value"}\n```\nTexto posterior'
        result = _extract_json_block(text)
        assert result == {"key": "value"}

    def test_json_puro(self):
        """Verifica parsing de texto que es solo JSON."""
        result = _extract_json_block('{"a": 1}')
        assert result == {"a": 1}

    def test_sin_json(self):
        """Verifica None cuando no hay JSON."""
        result = _extract_json_block("Solo texto plano sin JSON.")
        assert result is None

    def test_json_invalido_en_bloque(self):
        """Verifica None con JSON inválido dentro del bloque."""
        text = '```json\n{invalid json}\n```'
        result = _extract_json_block(text)
        assert result is None
