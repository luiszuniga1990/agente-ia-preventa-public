"""Tests unitarios para el handler de conexión WebSocket."""

from src.handlers.ws_connect import handler


class TestHandleConnect:
    """Tests para el evento $connect."""

    def test_connect_with_valid_token_returns_200(self):
        """Conexión exitosa con JWT presente en query string."""
        event = {
            "requestContext": {
                "routeKey": "$connect",
                "connectionId": "conn-123",
            },
            "queryStringParameters": {"token": "valid-jwt-token"},
        }
        result = handler(event, None)
        assert result["statusCode"] == 200

    def test_connect_without_token_returns_401(self):
        """Rechazo de conexión sin JWT."""
        event = {
            "requestContext": {
                "routeKey": "$connect",
                "connectionId": "conn-123",
            },
            "queryStringParameters": {},
        }
        result = handler(event, None)
        assert result["statusCode"] == 401

    def test_connect_with_empty_token_returns_401(self):
        """Rechazo de conexión con token vacío."""
        event = {
            "requestContext": {
                "routeKey": "$connect",
                "connectionId": "conn-123",
            },
            "queryStringParameters": {"token": ""},
        }
        result = handler(event, None)
        assert result["statusCode"] == 401

    def test_connect_with_whitespace_token_returns_401(self):
        """Rechazo de conexión con token solo espacios."""
        event = {
            "requestContext": {
                "routeKey": "$connect",
                "connectionId": "conn-123",
            },
            "queryStringParameters": {"token": "   "},
        }
        result = handler(event, None)
        assert result["statusCode"] == 401

    def test_connect_with_null_query_params_returns_401(self):
        """Rechazo cuando queryStringParameters es None."""
        event = {
            "requestContext": {
                "routeKey": "$connect",
                "connectionId": "conn-123",
            },
            "queryStringParameters": None,
        }
        result = handler(event, None)
        assert result["statusCode"] == 401

    def test_connect_without_query_params_key_returns_401(self):
        """Rechazo cuando no existe queryStringParameters."""
        event = {
            "requestContext": {
                "routeKey": "$connect",
                "connectionId": "conn-123",
            },
        }
        result = handler(event, None)
        assert result["statusCode"] == 401


class TestHandleDisconnect:
    """Tests para el evento $disconnect."""

    def test_disconnect_returns_200(self):
        """Desconexión exitosa."""
        event = {
            "requestContext": {
                "routeKey": "$disconnect",
                "connectionId": "conn-123",
            },
        }
        result = handler(event, None)
        assert result["statusCode"] == 200


class TestUnknownRoute:
    """Tests para rutas no reconocidas."""

    def test_unknown_route_returns_400(self):
        """Ruta desconocida retorna 400."""
        event = {
            "requestContext": {
                "routeKey": "$unknown",
                "connectionId": "conn-123",
            },
        }
        result = handler(event, None)
        assert result["statusCode"] == 400

    def test_empty_route_returns_400(self):
        """Ruta vacía retorna 400."""
        event = {
            "requestContext": {
                "routeKey": "",
                "connectionId": "conn-123",
            },
        }
        result = handler(event, None)
        assert result["statusCode"] == 400
