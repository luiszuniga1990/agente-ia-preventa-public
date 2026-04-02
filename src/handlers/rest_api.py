"""Handler REST principal — router para endpoints de la API.

Enruta peticiones REST a los handlers apropiados según
httpMethod y resource path. El JWT es validado por el
autorizador de Cognito en API Gateway; aquí solo se extrae
el user_id del requestContext.
"""

import json
import logging

from src.handlers import consolidation_handler, email_handler, pdf_handler

logger = logging.getLogger(__name__)


def handler(event: dict, context: object) -> dict:
    """Router principal para endpoints REST.

    Rutas soportadas:
        GET  /estimations                      — listar estimaciones
        GET  /estimations/{id}                 — detalle de estimación
        POST /estimations/{id}/export          — exportar PDF/CSV
        POST /estimations/{id}/consolidate     — consolidar con JSON externo
        POST /estimations/{id}/email           — enviar por correo
        GET  /conversations                    — listar conversaciones
        GET  /conversations/{id}               — detalle de conversación

    Args:
        event: Evento de API Gateway REST con autorizador Cognito.
        context: Contexto de Lambda.

    Returns:
        Respuesta HTTP con datos o error.
    """
    http_method = event.get("httpMethod", "")
    resource = event.get("resource", "")
    user_id = _extract_user_id(event)

    logger.info("REST %s %s user=%s", http_method, resource, user_id)

    try:
        route_key = f"{http_method} {resource}"
        route_handler = _get_route_handler(route_key)

        if route_handler is None:
            return _error_response(
                404, "NOT_FOUND",
                f"Ruta no encontrada: {http_method} {resource}",
            )

        # Inyectar user_id en el evento para que los handlers lo usen
        if "requestContext" not in event:
            event["requestContext"] = {}
        event["requestContext"]["authorizer"] = {"claims": {"sub": user_id}}

        return route_handler(event, context)

    except Exception as exc:
        logger.exception("Error en rest_api handler: %s", exc)
        return _error_response(500, "INTERNAL_ERROR", "Error interno del servidor")


def _extract_user_id(event: dict) -> str:
    """Extraer user_id del requestContext (Cognito authorizer).

    Args:
        event: Evento de API Gateway.

    Returns:
        user_id del usuario autenticado, o cadena vacía.
    """
    request_context = event.get("requestContext", {})
    authorizer = request_context.get("authorizer", {})
    claims = authorizer.get("claims", {})
    return claims.get("sub", "")


def _get_route_handler(route_key: str):
    """Obtener el handler correspondiente a una ruta.

    Args:
        route_key: Clave de ruta en formato "METHOD /resource".

    Returns:
        Función handler o None si la ruta no existe.
    """
    routes = {
        "GET /estimations": _handle_list_estimations,
        "GET /estimations/{id}": _handle_get_estimation,
        "POST /estimations/{id}/export": _handle_export,
        "POST /estimations/{id}/consolidate": _handle_consolidate,
        "POST /estimations/{id}/email": _handle_email,
        "GET /conversations": _handle_list_conversations,
        "GET /conversations/{id}": _handle_get_conversation,
    }
    return routes.get(route_key)


def _handle_list_estimations(event: dict, context: object) -> dict:
    """Listar estimaciones del usuario autenticado.

    Args:
        event: Evento de API Gateway.
        context: Contexto de Lambda.

    Returns:
        Respuesta HTTP con lista de estimaciones.
    """
    import boto3
    from dataclasses import asdict
    from src.services import estimation_repo

    user_id = _extract_user_id(event)
    if not user_id:
        return _error_response(401, "AUTH_ERROR", "Usuario no autenticado")

    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
    estimations = estimation_repo.list_estimations(dynamodb, user_id)

    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(
            [asdict(e) for e in estimations], default=str
        ),
    }


def _handle_get_estimation(event: dict, context: object) -> dict:
    """Obtener detalle de una estimación.

    Args:
        event: Evento de API Gateway.
        context: Contexto de Lambda.

    Returns:
        Respuesta HTTP con la estimación o error 404.
    """
    import boto3
    from dataclasses import asdict
    from src.services import estimation_repo

    path_params = event.get("pathParameters") or {}
    estimation_id = path_params.get("id", "")

    if not estimation_id:
        return _error_response(400, "VALIDATION_ERROR", "estimation_id es requerido")

    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
    estimation = estimation_repo.get_estimation(dynamodb, estimation_id)

    if not estimation:
        return _error_response(404, "NOT_FOUND", "Estimación no encontrada")

    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(asdict(estimation), default=str),
    }


def _handle_export(event: dict, context: object) -> dict:
    """Delegar exportación PDF/CSV al pdf_handler.

    Args:
        event: Evento de API Gateway.
        context: Contexto de Lambda.

    Returns:
        Respuesta del pdf_handler.
    """
    return pdf_handler.handler(event, context)


def _handle_consolidate(event: dict, context: object) -> dict:
    """Delegar consolidación al consolidation_handler.

    Args:
        event: Evento de API Gateway.
        context: Contexto de Lambda.

    Returns:
        Respuesta del consolidation_handler.
    """
    return consolidation_handler.handler(event, context)


def _handle_email(event: dict, context: object) -> dict:
    """Delegar envío de email al email_handler.

    Args:
        event: Evento de API Gateway.
        context: Contexto de Lambda.

    Returns:
        Respuesta del email_handler.
    """
    return email_handler.handler(event, context)


def _handle_list_conversations(event: dict, context: object) -> dict:
    """Listar conversaciones del usuario autenticado.

    Args:
        event: Evento de API Gateway.
        context: Contexto de Lambda.

    Returns:
        Respuesta HTTP con lista de conversaciones.
    """
    import boto3
    from dataclasses import asdict
    from src.services import conversation_repo

    user_id = _extract_user_id(event)
    if not user_id:
        return _error_response(401, "AUTH_ERROR", "Usuario no autenticado")

    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
    conversations = conversation_repo.list_conversations(dynamodb, user_id)

    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(
            [asdict(c) for c in conversations], default=str
        ),
    }


def _handle_get_conversation(event: dict, context: object) -> dict:
    """Obtener detalle de una conversación.

    Args:
        event: Evento de API Gateway.
        context: Contexto de Lambda.

    Returns:
        Respuesta HTTP con la conversación o error 404.
    """
    import boto3
    from dataclasses import asdict
    from src.services import conversation_repo

    path_params = event.get("pathParameters") or {}
    conversation_id = path_params.get("id", "")

    if not conversation_id:
        return _error_response(
            400, "VALIDATION_ERROR", "conversation_id es requerido"
        )

    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
    conversation = conversation_repo.get_conversation(dynamodb, conversation_id)

    if not conversation:
        return _error_response(404, "NOT_FOUND", "Conversación no encontrada")

    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(asdict(conversation), default=str),
    }


def _error_response(status_code: int, code: str, message: str) -> dict:
    """Construir respuesta de error estándar.

    Args:
        status_code: Código HTTP.
        code: Código de error interno.
        message: Mensaje descriptivo.

    Returns:
        Diccionario con la respuesta HTTP.
    """
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"error": {"code": code, "message": message}}),
    }
