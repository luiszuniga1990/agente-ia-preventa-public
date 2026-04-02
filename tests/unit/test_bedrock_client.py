"""Tests unitarios para el cliente de Bedrock (bedrock_client).

Verifica invocación del modelo, retry con backoff, manejo de errores
y extracción de respuestas.
"""

from unittest.mock import MagicMock, patch

import pytest
from botocore.exceptions import ClientError

from src.services.bedrock_client import (
    DEFAULT_ERROR_MESSAGE,
    MODEL_ID,
    _build_messages,
    _build_system,
    _extract_text,
    invoke_model,
)


def _make_converse_response(text: str) -> dict:
    """Crear respuesta simulada de la API Converse."""
    return {
        "output": {
            "message": {
                "role": "assistant",
                "content": [{"text": text}],
            }
        },
        "usage": {"inputTokens": 10, "outputTokens": 20},
    }


def _make_client_error(code: str, message: str = "error") -> ClientError:
    """Crear un ClientError simulado."""
    return ClientError(
        {"Error": {"Code": code, "Message": message}},
        "Converse",
    )


class TestInvokeModel:
    """Tests para la función invoke_model."""

    def test_invocacion_exitosa(self):
        """Verifica invocación exitosa con respuesta válida."""
        mock_client = MagicMock()
        mock_client.converse.return_value = _make_converse_response(
            "Estimación generada correctamente."
        )

        result = invoke_model(
            mock_client,
            prompt="Estimar Amazon Quick para 50 usuarios",
            system_prompt="Eres un asistente de preventa.",
        )

        assert result == "Estimación generada correctamente."
        mock_client.converse.assert_called_once()
        call_kwargs = mock_client.converse.call_args[1]
        assert call_kwargs["modelId"] == MODEL_ID
        assert len(call_kwargs["messages"]) == 1
        assert call_kwargs["messages"][0]["role"] == "user"

    def test_invocacion_con_historial(self):
        """Verifica que el historial conversacional se incluye en los mensajes."""
        mock_client = MagicMock()
        mock_client.converse.return_value = _make_converse_response("OK")

        history = [
            {"role": "user", "content": "Hola"},
            {"role": "assistant", "content": "¿En qué puedo ayudarte?"},
        ]

        invoke_model(
            mock_client,
            prompt="Necesito una estimación",
            system_prompt="Sistema",
            conversation_history=history,
        )

        call_kwargs = mock_client.converse.call_args[1]
        messages = call_kwargs["messages"]
        assert len(messages) == 3
        assert messages[0]["role"] == "user"
        assert messages[1]["role"] == "assistant"
        assert messages[2]["role"] == "user"

    def test_invocacion_sin_system_prompt(self):
        """Verifica que sin system prompt no se envía el campo system."""
        mock_client = MagicMock()
        mock_client.converse.return_value = _make_converse_response("OK")

        invoke_model(mock_client, prompt="Test")

        call_kwargs = mock_client.converse.call_args[1]
        assert "system" not in call_kwargs

    @patch("src.services.bedrock_client._wait_backoff")
    def test_retry_en_throttling(self, mock_backoff):
        """Verifica retry con backoff en ThrottlingException."""
        mock_client = MagicMock()
        mock_client.converse.side_effect = [
            _make_client_error("ThrottlingException"),
            _make_converse_response("Respuesta después de retry"),
        ]

        result = invoke_model(mock_client, prompt="Test")

        assert result == "Respuesta después de retry"
        assert mock_client.converse.call_count == 2
        mock_backoff.assert_called_once_with(1)

    @patch("src.services.bedrock_client._wait_backoff")
    def test_retry_en_service_unavailable(self, mock_backoff):
        """Verifica retry en ServiceUnavailableException."""
        mock_client = MagicMock()
        mock_client.converse.side_effect = [
            _make_client_error("ServiceUnavailableException"),
            _make_converse_response("Recuperado"),
        ]

        result = invoke_model(mock_client, prompt="Test")

        assert result == "Recuperado"
        assert mock_client.converse.call_count == 2

    @patch("src.services.bedrock_client._wait_backoff")
    def test_fallo_despues_de_max_reintentos(self, mock_backoff):
        """Verifica RuntimeError después de agotar reintentos."""
        mock_client = MagicMock()
        mock_client.converse.side_effect = _make_client_error(
            "ThrottlingException"
        )

        with pytest.raises(RuntimeError, match="temporalmente fuera de servicio"):
            invoke_model(mock_client, prompt="Test")

        assert mock_client.converse.call_count == 3

    @patch("src.services.bedrock_client._wait_backoff")
    def test_error_inesperado_con_retry(self, mock_backoff):
        """Verifica retry en excepciones genéricas."""
        mock_client = MagicMock()
        mock_client.converse.side_effect = [
            Exception("Connection reset"),
            _make_converse_response("OK"),
        ]

        result = invoke_model(mock_client, prompt="Test")
        assert result == "OK"

    def test_error_no_expone_detalles_tecnicos(self):
        """Verifica que el mensaje de error no contiene detalles técnicos."""
        mock_client = MagicMock()
        mock_client.converse.side_effect = _make_client_error(
            "ValidationException", "Model not found: xyz-123"
        )

        with pytest.raises(RuntimeError) as exc_info:
            invoke_model(mock_client, prompt="Test")

        error_msg = str(exc_info.value)
        assert error_msg == DEFAULT_ERROR_MESSAGE
        assert "ValidationException" not in error_msg
        assert "xyz-123" not in error_msg


class TestBuildMessages:
    """Tests para _build_messages."""

    def test_solo_prompt(self):
        """Verifica construcción con solo el prompt actual."""
        messages = _build_messages("Hola", None)
        assert len(messages) == 1
        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == [{"text": "Hola"}]

    def test_con_historial(self):
        """Verifica construcción con historial previo."""
        history = [
            {"role": "user", "content": "Msg 1"},
            {"role": "assistant", "content": "Resp 1"},
        ]
        messages = _build_messages("Msg 2", history)
        assert len(messages) == 3
        assert messages[2]["content"] == [{"text": "Msg 2"}]


class TestBuildSystem:
    """Tests para _build_system."""

    def test_con_system_prompt(self):
        """Verifica bloque de sistema con prompt."""
        result = _build_system("Eres un asistente.")
        assert result == [{"text": "Eres un asistente."}]

    def test_sin_system_prompt(self):
        """Verifica lista vacía sin prompt."""
        assert _build_system("") == []


class TestExtractText:
    """Tests para _extract_text."""

    def test_respuesta_valida(self):
        """Verifica extracción de texto de respuesta válida."""
        response = _make_converse_response("Texto de respuesta")
        assert _extract_text(response) == "Texto de respuesta"

    def test_respuesta_sin_contenido(self):
        """Verifica respuesta vacía cuando no hay bloques de contenido."""
        response = {"output": {"message": {"content": []}}}
        assert _extract_text(response) == ""

    def test_respuesta_malformada(self):
        """Verifica RuntimeError con respuesta malformada."""
        with pytest.raises(RuntimeError, match="temporalmente fuera de servicio"):
            _extract_text(None)
