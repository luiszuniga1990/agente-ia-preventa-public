"""Tests unitarios para las funciones de flujo de estimación en chat_handler."""

import json

from src.handlers.chat_handler import (
    _check_consolidation_trigger,
    _check_email_trigger,
    _check_estimation_trigger,
    _check_recalculation_trigger,
    _extract_json_from_response,
)


class TestCheckEstimationTrigger:
    """Tests para detección de trigger de estimación."""

    def test_detects_estimation_data_in_response(self):
        """Detecta datos de estimación en bloque JSON."""
        response = '''Aquí está la estimación:
```json
{
    "service": "amazon_quick",
    "parameters": {"num_users": 100},
    "partner_data": {
        "partner_name": "Acme",
        "partner_email": "a@b.com",
        "region": "us-east-1",
        "end_customer": "Corp"
    }
}
```'''
        result = _check_estimation_trigger(response)
        assert result is not None
        assert result["service"] == "amazon_quick"

    def test_returns_none_for_empty_response(self):
        assert _check_estimation_trigger("") is None

    def test_returns_none_for_none_response(self):
        assert _check_estimation_trigger(None) is None

    def test_returns_none_without_json_block(self):
        assert _check_estimation_trigger("Solo texto sin JSON") is None

    def test_returns_none_for_unsupported_service(self):
        """Rechaza servicios no soportados."""
        response = '''```json
{
    "service": "servicio_invalido",
    "parameters": {},
    "partner_data": {
        "partner_name": "A", "partner_email": "a@b.com",
        "region": "us", "end_customer": "C"
    }
}
```'''
        assert _check_estimation_trigger(response) is None

    def test_returns_none_missing_partner_fields(self):
        """Rechaza si faltan campos del partner."""
        response = '''```json
{
    "service": "amazon_quick",
    "parameters": {},
    "partner_data": {"partner_name": "A"}
}
```'''
        assert _check_estimation_trigger(response) is None

    def test_returns_none_missing_required_keys(self):
        """Rechaza si faltan claves requeridas."""
        response = '''```json
{"service": "amazon_quick"}
```'''
        assert _check_estimation_trigger(response) is None


class TestExtractJsonFromResponse:
    """Tests para extracción de JSON de respuestas."""

    def test_extracts_json_block(self):
        text = 'Texto antes ```json\n{"key": "value"}\n``` texto después'
        result = _extract_json_from_response(text)
        assert result == {"key": "value"}

    def test_returns_none_without_json_block(self):
        assert _extract_json_from_response("No JSON here") is None

    def test_returns_none_for_invalid_json(self):
        text = '```json\n{invalid json}\n```'
        assert _extract_json_from_response(text) is None

    def test_returns_none_for_empty_string(self):
        assert _extract_json_from_response("") is None

    def test_returns_none_for_unclosed_block(self):
        text = '```json\n{"key": "value"}'
        assert _extract_json_from_response(text) is None


class TestCheckConsolidationTrigger:
    """Tests para detección de trigger de consolidación."""

    def test_detects_consolidar_keyword(self):
        assert _check_consolidation_trigger("Quiero consolidar estimaciones") is True

    def test_detects_consolidate_english(self):
        assert _check_consolidation_trigger("I want to consolidate") is True

    def test_detects_json_externo(self):
        assert _check_consolidation_trigger("Tengo un json externo") is True

    def test_returns_false_for_unrelated_message(self):
        assert _check_consolidation_trigger("Hola, necesito ayuda") is False

    def test_returns_false_for_empty_message(self):
        assert _check_consolidation_trigger("") is False


class TestCheckEmailTrigger:
    """Tests para detección de trigger de email."""

    def test_detects_enviar_por_correo(self):
        assert _check_email_trigger("Quiero enviar por correo", "") is True

    def test_detects_send_email_english(self):
        assert _check_email_trigger("Please send email", "") is True

    def test_detects_enviar_email(self):
        assert _check_email_trigger("enviar email al partner", "") is True

    def test_returns_false_for_unrelated(self):
        assert _check_email_trigger("Necesito una estimación", "") is False

    def test_returns_false_for_empty(self):
        assert _check_email_trigger("", "") is False


class TestCheckRecalculationTrigger:
    """Tests para detección de trigger de recálculo."""

    def test_detects_recalcular_with_prior_estimation(self):
        messages = [
            {"role": "assistant", "content": "estimation_id: abc-123"}
        ]
        assert _check_recalculation_trigger("Quiero recalcular", messages) is True

    def test_detects_modify_with_prior_estimation(self):
        messages = [
            {"role": "assistant", "content": "La estimación fue generada"}
        ]
        assert _check_recalculation_trigger("Quiero modificar parámetros", messages) is True

    def test_returns_false_without_prior_estimation(self):
        messages = [
            {"role": "assistant", "content": "Hola, ¿en qué puedo ayudar?"}
        ]
        assert _check_recalculation_trigger("Quiero recalcular", messages) is False

    def test_returns_false_without_keyword(self):
        messages = [
            {"role": "assistant", "content": "estimation_id: abc"}
        ]
        assert _check_recalculation_trigger("Hola", messages) is False

    def test_returns_false_for_empty_message(self):
        assert _check_recalculation_trigger("", []) is False
