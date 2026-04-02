"""Handler REST para envío de estimaciones por correo electrónico.

Endpoint: POST /estimations/{id}/email
Recibe estimation_id, recipient_email y language.
Obtiene la estimación, genera PDF, envía email vía SES.
"""

import json
import logging
import os

import boto3

from src.services import estimation_repo
from src.services.email_service import send_estimation_email
from src.services.pdf_generator import generate_pdf

logger = logging.getLogger(__name__)


def handler(event: dict, context: object) -> dict:
    """Endpoint REST o invocación interna para enviar estimación por email.

    Recibe estimation_id de pathParameters, recipient_email y language del body.
    Obtiene la estimación de DynamoDB, genera el PDF y envía el correo.

    Args:
        event: Evento de API Gateway REST o invocación interna.
        context: Contexto de Lambda.

    Returns:
        Respuesta HTTP con resultado del envío o error.
    """
    try:
        # Extraer parámetros
        path_params = event.get("pathParameters") or {}
        estimation_id = path_params.get("id", "")

        body = event.get("body", "{}")
        if isinstance(body, str):
            body = json.loads(body) if body else {}

        recipient_email = body.get("recipient_email", "")
        language = body.get("language", "es")

        if not estimation_id:
            return _error_response(400, "VALIDATION_ERROR", "estimation_id es requerido")

        if not recipient_email:
            return _error_response(
                400, "VALIDATION_ERROR", "recipient_email es requerido"
            )

        # Obtener estimación de DynamoDB
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        estimation = estimation_repo.get_estimation(dynamodb, estimation_id)

        if not estimation:
            return _error_response(404, "NOT_FOUND", "Estimación no encontrada")

        # Generar PDF
        try:
            pdf_bytes = generate_pdf(estimation, language)
        except Exception as exc:
            logger.warning("Error generando PDF para email: %s", exc)
            return _error_response(
                500,
                "SERVICE_ERROR",
                "Error al generar PDF. Puede descargar la estimación manualmente.",
            )

        # Enviar email
        ses_client = boto3.client("ses", region_name="us-east-1")
        result = send_estimation_email(
            ses_client, estimation, recipient_email, pdf_bytes, language
        )

        if result["status"] == "failed":
            error_msg = result.get("error", "Error desconocido")
            return {
                "statusCode": 500,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({
                    "error": {
                        "code": "SERVICE_ERROR",
                        "message": (
                            "Error al enviar correo. "
                            "Puede reintentar o descargar la estimación manualmente."
                        ),
                    },
                    "retry_available": True,
                }),
            }

        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({
                "message_id": result["message_id"],
                "status": result["status"],
            }),
        }

    except json.JSONDecodeError:
        return _error_response(400, "VALIDATION_ERROR", "Body JSON inválido")
    except Exception as exc:
        logger.exception("Error en email_handler: %s", exc)
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
