"""Tests unitarios para el handler REST principal."""

import json
from unittest.mock import MagicMock, patch

from src.handlers.rest_api import (
    _extract_user_id,
    _get_route_handler,
    handler,
)


class TestExtractUserId:
    """Tests para extracción de user_id del requestContext."""

    def test_extracts_user_id_from_cognito_claims(self):
        event = {
            "requestContext": {
                "authorizer": {"claims": {"sub": "user-123"}}
            }
        }
        assert _extract_user_id(event) == "user-123"

    def test_returns_empty_when_no_authorizer(self):
        event = {"requestContext": {}}
        assert _extract_user_id(event) == ""

    def test_returns_empty_when_no_request_context(self):
        event = {}
        assert _extract_user_id(event) == ""

    def test_returns_empty_when_no_claims(self):
        event = {"requestContext": {"authorizer": {}}}
        assert _extract_user_id(event) == ""


class TestGetRouteHandler:
    """Tests para el router de rutas."""

    def test_get_estimations_route(self):
        assert _get_route_handler("GET /estimations") is not None

    def test_get_estimation_by_id_route(self):
        assert _get_route_handler("GET /estimations/{id}") is not None

    def test_post_export_route(self):
        assert _get_route_handler("POST /estimations/{id}/export") is not None

    def test_post_consolidate_route(self):
        assert _get_route_handler("POST /estimations/{id}/consolidate") is not None

    def test_post_email_route(self):
        assert _get_route_handler("POST /estimations/{id}/email") is not None

    def test_get_conversations_route(self):
        assert _get_route_handler("GET /conversations") is not None

    def test_get_conversation_by_id_route(self):
        assert _get_route_handler("GET /conversations/{id}") is not None

    def test_unknown_route_returns_none(self):
        assert _get_route_handler("DELETE /unknown") is None


class TestHandler:
    """Tests para el handler principal."""

    def test_unknown_route_returns_404(self):
        """Ruta desconocida retorna 404."""
        event = {
            "httpMethod": "DELETE",
            "resource": "/unknown",
            "requestContext": {"authorizer": {"claims": {"sub": "u1"}}},
        }
        result = handler(event, None)
        assert result["statusCode"] == 404
        body = json.loads(result["body"])
        assert body["error"]["code"] == "NOT_FOUND"

    @patch("src.handlers.rest_api._handle_list_estimations")
    def test_routes_get_estimations(self, mock_handler):
        """GET /estimations se enruta correctamente."""
        mock_handler.return_value = {"statusCode": 200, "body": "[]"}
        event = {
            "httpMethod": "GET",
            "resource": "/estimations",
            "requestContext": {"authorizer": {"claims": {"sub": "u1"}}},
        }
        result = handler(event, None)
        assert result["statusCode"] == 200
        mock_handler.assert_called_once()

    @patch("src.handlers.rest_api._handle_get_estimation")
    def test_routes_get_estimation_by_id(self, mock_handler):
        """GET /estimations/{id} se enruta correctamente."""
        mock_handler.return_value = {"statusCode": 200, "body": "{}"}
        event = {
            "httpMethod": "GET",
            "resource": "/estimations/{id}",
            "pathParameters": {"id": "est-1"},
            "requestContext": {"authorizer": {"claims": {"sub": "u1"}}},
        }
        result = handler(event, None)
        assert result["statusCode"] == 200

    @patch("src.handlers.rest_api.pdf_handler")
    def test_routes_export_to_pdf_handler(self, mock_pdf):
        """POST /estimations/{id}/export delega a pdf_handler."""
        mock_pdf.handler.return_value = {"statusCode": 200, "body": "{}"}
        event = {
            "httpMethod": "POST",
            "resource": "/estimations/{id}/export",
            "pathParameters": {"id": "est-1"},
            "body": json.dumps({"format": "pdf"}),
            "requestContext": {"authorizer": {"claims": {"sub": "u1"}}},
        }
        result = handler(event, None)
        assert result["statusCode"] == 200
        mock_pdf.handler.assert_called_once()

    @patch("src.handlers.rest_api.consolidation_handler")
    def test_routes_consolidate(self, mock_consol):
        """POST /estimations/{id}/consolidate delega a consolidation_handler."""
        mock_consol.handler.return_value = {"statusCode": 200, "body": "{}"}
        event = {
            "httpMethod": "POST",
            "resource": "/estimations/{id}/consolidate",
            "pathParameters": {"id": "est-1"},
            "body": json.dumps({"external_json": {}}),
            "requestContext": {"authorizer": {"claims": {"sub": "u1"}}},
        }
        result = handler(event, None)
        assert result["statusCode"] == 200

    @patch("src.handlers.rest_api.email_handler")
    def test_routes_email(self, mock_email):
        """POST /estimations/{id}/email delega a email_handler."""
        mock_email.handler.return_value = {"statusCode": 200, "body": "{}"}
        event = {
            "httpMethod": "POST",
            "resource": "/estimations/{id}/email",
            "pathParameters": {"id": "est-1"},
            "body": json.dumps({"recipient_email": "a@b.com"}),
            "requestContext": {"authorizer": {"claims": {"sub": "u1"}}},
        }
        result = handler(event, None)
        assert result["statusCode"] == 200

    @patch("src.handlers.rest_api._handle_list_conversations")
    def test_routes_get_conversations(self, mock_handler):
        """GET /conversations se enruta correctamente."""
        mock_handler.return_value = {"statusCode": 200, "body": "[]"}
        event = {
            "httpMethod": "GET",
            "resource": "/conversations",
            "requestContext": {"authorizer": {"claims": {"sub": "u1"}}},
        }
        result = handler(event, None)
        assert result["statusCode"] == 200

    @patch("src.handlers.rest_api._handle_get_conversation")
    def test_routes_get_conversation_by_id(self, mock_handler):
        """GET /conversations/{id} se enruta correctamente."""
        mock_handler.return_value = {"statusCode": 200, "body": "{}"}
        event = {
            "httpMethod": "GET",
            "resource": "/conversations/{id}",
            "pathParameters": {"id": "conv-1"},
            "requestContext": {"authorizer": {"claims": {"sub": "u1"}}},
        }
        result = handler(event, None)
        assert result["statusCode"] == 200
