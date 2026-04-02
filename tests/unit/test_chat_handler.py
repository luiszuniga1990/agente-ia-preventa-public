"""Tests unitarios para el handler de mensajes de chat."""

import json
from unittest.mock import MagicMock, patch

from src.handlers.chat_handler import (
    _build_conversation_history,
    _get_all_pricing,
    _get_or_create_conversation,
    _parse_body,
    handler,
)


class TestParseBody:
    """Tests para parseo del body del evento."""

    def test_parse_valid_json_body(self):
        event = {"body": json.dumps({"message": "hola", "conversation_id": "c1"})}
        result = _parse_body(event)
        assert result == {"message": "hola", "conversation_id": "c1"}

    def test_parse_empty_body_returns_none(self):
        event = {"body": ""}
        assert _parse_body(event) is None

    def test_parse_missing_body_returns_none(self):
        event = {}
        assert _parse_body(event) is None

    def test_parse_invalid_json_returns_none(self):
        event = {"body": "not-json{"}
        assert _parse_body(event) is None


class TestBuildConversationHistory:
    """Tests para construcción del historial conversacional."""

    def test_empty_messages_returns_empty_list(self):
        assert _build_conversation_history([]) == []

    def test_builds_history_from_messages(self):
        messages = [
            {"role": "user", "content": "Hola", "timestamp": "2024-01-01"},
            {"role": "assistant", "content": "¡Hola!", "timestamp": "2024-01-01"},
        ]
        result = _build_conversation_history(messages)
        assert len(result) == 2
        assert result[0] == {"role": "user", "content": "Hola"}
        assert result[1] == {"role": "assistant", "content": "¡Hola!"}

    def test_skips_messages_with_empty_content(self):
        messages = [
            {"role": "user", "content": "Hola"},
            {"role": "assistant", "content": ""},
            {"role": "user", "content": "Otro"},
        ]
        result = _build_conversation_history(messages)
        assert len(result) == 2


class TestGetOrCreateConversation:
    """Tests para obtener o crear conversación."""

    @patch("src.handlers.chat_handler.conversation_repo")
    def test_returns_existing_conversation(self, mock_repo):
        mock_conv = MagicMock()
        mock_conv.conversation_id = "existing-id"
        mock_repo.get_conversation.return_value = mock_conv
        dynamodb = MagicMock()

        result = _get_or_create_conversation(dynamodb, "existing-id", "user-1")
        assert result.conversation_id == "existing-id"
        mock_repo.get_conversation.assert_called_once_with(dynamodb, "existing-id")

    @patch("src.handlers.chat_handler.conversation_repo")
    def test_creates_new_when_id_empty(self, mock_repo):
        mock_conv = MagicMock()
        mock_conv.conversation_id = "new-id"
        mock_repo.create_conversation.return_value = mock_conv
        dynamodb = MagicMock()

        result = _get_or_create_conversation(dynamodb, "", "user-1")
        assert result.conversation_id == "new-id"
        mock_repo.create_conversation.assert_called_once()

    @patch("src.handlers.chat_handler.conversation_repo")
    def test_creates_new_when_not_found(self, mock_repo):
        mock_repo.get_conversation.return_value = None
        mock_conv = MagicMock()
        mock_repo.create_conversation.return_value = mock_conv
        dynamodb = MagicMock()

        result = _get_or_create_conversation(dynamodb, "missing-id", "user-1")
        mock_repo.create_conversation.assert_called_once()


class TestGetAllPricing:
    """Tests para obtención de precios de todos los servicios."""

    @patch("src.handlers.chat_handler.pricing_repo")
    def test_gets_pricing_for_all_services(self, mock_repo):
        mock_repo.get_pricing.return_value = []
        dynamodb = MagicMock()

        result = _get_all_pricing(dynamodb)
        assert result == []
        assert mock_repo.get_pricing.call_count == 3


class TestHandler:
    """Tests de integración para el handler principal."""

    def test_empty_message_returns_200(self):
        """Mensaje vacío se ignora y retorna 200."""
        event = {
            "requestContext": {
                "connectionId": "conn-1",
                "domainName": "api.example.com",
                "stage": "prod",
            },
            "body": json.dumps({"message": "", "conversation_id": "c1"}),
        }
        result = handler(event, None)
        assert result["statusCode"] == 200

    def test_whitespace_message_returns_200(self):
        """Mensaje con solo espacios se ignora."""
        event = {
            "requestContext": {
                "connectionId": "conn-1",
                "domainName": "api.example.com",
                "stage": "prod",
            },
            "body": json.dumps({"message": "   ", "conversation_id": "c1"}),
        }
        result = handler(event, None)
        assert result["statusCode"] == 200

    def test_invalid_body_returns_200(self):
        """Body inválido se ignora y retorna 200."""
        event = {
            "requestContext": {
                "connectionId": "conn-1",
                "domainName": "api.example.com",
                "stage": "prod",
            },
            "body": "not-json",
        }
        result = handler(event, None)
        assert result["statusCode"] == 200

    def test_missing_body_returns_200(self):
        """Body ausente se ignora y retorna 200."""
        event = {
            "requestContext": {
                "connectionId": "conn-1",
                "domainName": "api.example.com",
                "stage": "prod",
            },
        }
        result = handler(event, None)
        assert result["statusCode"] == 200

    @patch("src.handlers.chat_handler._send_error_to_client")
    @patch("src.handlers.chat_handler.boto3")
    def test_bedrock_error_returns_500(self, mock_boto3, mock_send_error):
        """Error de Bedrock retorna 500 y envía error al cliente."""
        mock_dynamodb = MagicMock()
        mock_bedrock = MagicMock()
        mock_apigw = MagicMock()

        mock_boto3.resource.return_value = mock_dynamodb
        mock_boto3.client.side_effect = [mock_bedrock, mock_apigw]

        # Simular que get_conversation falla
        mock_table = MagicMock()
        mock_dynamodb.Table.return_value = mock_table
        mock_table.query.side_effect = Exception("DynamoDB error")

        event = {
            "requestContext": {
                "connectionId": "conn-1",
                "domainName": "api.example.com",
                "stage": "prod",
            },
            "body": json.dumps({"message": "Hola", "conversation_id": "c1"}),
        }
        result = handler(event, None)
        assert result["statusCode"] == 500
        mock_send_error.assert_called_once()

    @patch("src.handlers.chat_handler._post_to_connection")
    @patch("src.handlers.chat_handler.invoke_model")
    @patch("src.handlers.chat_handler.pricing_repo")
    @patch("src.handlers.chat_handler.conversation_repo")
    @patch("src.handlers.chat_handler.boto3")
    def test_successful_message_flow(
        self, mock_boto3, mock_conv_repo, mock_pricing_repo,
        mock_invoke, mock_post
    ):
        """Flujo exitoso: mensaje → Bedrock → respuesta al cliente."""
        mock_dynamodb = MagicMock()
        mock_bedrock = MagicMock()
        mock_apigw = MagicMock()

        mock_boto3.resource.return_value = mock_dynamodb
        mock_boto3.client.side_effect = [mock_bedrock, mock_apigw]

        # Configurar mocks
        mock_conv = MagicMock()
        mock_conv.conversation_id = "conv-123"
        mock_conv.user_id = "user-1"
        mock_conv.messages = []
        mock_conv_repo.get_conversation.return_value = mock_conv
        mock_pricing_repo.get_pricing.return_value = []
        mock_invoke.return_value = "Respuesta del agente"

        event = {
            "requestContext": {
                "connectionId": "conn-1",
                "domainName": "api.example.com",
                "stage": "prod",
            },
            "body": json.dumps({
                "message": "Necesito una estimación de Amazon Quick",
                "conversation_id": "conv-123",
            }),
        }
        result = handler(event, None)
        assert result["statusCode"] == 200

        # Verificar que se guardaron ambos mensajes
        assert mock_conv_repo.add_message.call_count == 2
        calls = mock_conv_repo.add_message.call_args_list
        assert calls[0].args[3] == "user"
        assert calls[1].args[3] == "assistant"

        # Verificar que se envió respuesta al cliente
        mock_post.assert_called_once()
        payload = mock_post.call_args.args[2]
        assert payload["conversation_id"] == "conv-123"
        assert payload["response"] == "Respuesta del agente"
