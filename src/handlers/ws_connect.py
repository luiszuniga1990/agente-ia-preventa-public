"""Handler de conexión y desconexión WebSocket.

Maneja los eventos $connect y $disconnect de API Gateway WebSocket.
Valida la presencia del token JWT en el query string al conectar.
En producción, la validación real del JWT la realiza el autorizador
de Cognito en API Gateway.
"""

import logging

logger = logging.getLogger(__name__)


def handler(event: dict, context) -> dict:
    """Manejar eventos de conexión y desconexión WebSocket.

    Args:
        event: Evento de API Gateway WebSocket con requestContext.
        context: Contexto de Lambda (no utilizado).

    Returns:
        Respuesta HTTP con statusCode 200 (éxito) o 401 (no autorizado).
    """
    route_key = event.get("requestContext", {}).get("routeKey", "")
    connection_id = event.get("requestContext", {}).get("connectionId", "")

    if route_key == "$connect":
        return _handle_connect(event, connection_id)

    if route_key == "$disconnect":
        return _handle_disconnect(connection_id)

    logger.warning("Ruta no reconocida: %s", route_key)
    return {"statusCode": 400}


def _handle_connect(event: dict, connection_id: str) -> dict:
    """Procesar evento $connect: validar token JWT del query string.

    Verifica que el parámetro 'token' exista en los queryStringParameters.
    La validación criptográfica real del JWT la realiza el autorizador
    de Cognito configurado en API Gateway.

    Args:
        event: Evento de API Gateway WebSocket.
        connection_id: ID de la conexión WebSocket.

    Returns:
        Respuesta con statusCode 200 si el token está presente, 401 si no.
    """
    query_params = event.get("queryStringParameters") or {}
    token = query_params.get("token", "")

    if not token or not token.strip():
        logger.warning(
            "Conexión rechazada: token JWT ausente. connectionId=%s",
            connection_id,
        )
        return {"statusCode": 401}

    logger.info(
        "Conexión WebSocket establecida. connectionId=%s", connection_id
    )
    return {"statusCode": 200}


def _handle_disconnect(connection_id: str) -> dict:
    """Procesar evento $disconnect: limpiar recursos de la conexión.

    Args:
        connection_id: ID de la conexión WebSocket a limpiar.

    Returns:
        Respuesta con statusCode 200.
    """
    logger.info(
        "Conexión WebSocket cerrada. connectionId=%s", connection_id
    )
    return {"statusCode": 200}
