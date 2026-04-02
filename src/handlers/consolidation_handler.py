"""Handler REST para consolidación de estimaciones externas.

Endpoint: POST /estimations/{id}/consolidate
Recibe estimation_id y external_json del body.
Invoca consolidation_service para combinar estimaciones.
"""

import json
import logging
import os

import boto3

from src.services import consolidation_service
from src.utils.validators import MAX_JSON_SIZE_BYTES

logger = logging.getLogger(__name__)


def handler(event: dict, context: object) -> dict:
    """Endpoint REST para consolidar estimaciones.

    Recibe estimation_id de pathParameters y external_json del body.
    Valida tamaño del JSON (< 1 MB), invoca consolidation_service
    y retorna la estimación consolidada.

    Args:
        event: Evento de API Gateway REST.
        context: Contexto de Lambda.

    Returns:
        Respuesta HTTP con estimación consolidada o error.
    """
    try:
        # Extraer parámetros
        path_params = event.get("pathParameters") or {}
        estimation_id = path_params.get("id", "")

        raw_body = event.get("body", "")
        if isinstance(raw_body, str):
            if not raw_body.strip():
                return _error_response(400, "VALIDATION_ERROR", "Body vacío")
            # Verificar tamaño antes de parsear
            if len(raw_body.encode("utf-8")) > MAX_JSON_SIZE_BYTES:
                return _error_response(
                    400,
                    "VALIDATION_ERROR",
                    "El archivo excede el tamaño máximo permitido de 1 MB",
                )
            try:
                body = json.loads(raw_body)
            except json.JSONDecodeError as exc:
                return _error_response(
                    400, "VALIDATION_ERROR", f"JSON inválido: {exc}"
                )
        else:
            body = raw_body

        if not estimation_id:
            return _error_response(400, "VALIDATION_ERROR", "estimation_id es requerido")

        external_json = body.get("external_json")
        if external_json is None:
            return _error_response(
                400, "VALIDATION_ERROR", "external_json es requerido en el body"
            )

        # Invocar servicio de consolidación
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        consolidated = consolidation_service.consolidate(
            dynamodb, estimation_id, external_json
        )

        # Construir respuesta
        from dataclasses import asdict
        result = asdict(consolidated)

        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(result, default=str),
        }

    except ValueError as exc:
        error_msg = str(exc)
        if "no encontrada" in error_msg.lower():
            return _error_response(404, "NOT_FOUND", error_msg)
        return _error_response(400, "VALIDATION_ERROR", error_msg)
    except Exception as exc:
        logger.exception("Error en consolidation_handler: %s", exc)
        return _error_response(500, "INTERNAL_ERROR", "Error interno del servidor")


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
