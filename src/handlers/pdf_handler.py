"""Handler REST para generación y descarga de PDF/CSV.

Endpoint: POST /estimations/{id}/export
Recibe estimation_id, format (pdf/csv) y language.
Genera el archivo, lo sube a S3 y retorna URL pre-firmada.
"""

import json
import logging
import os

import boto3

from src.services import estimation_repo
from src.services.pdf_generator import generate_csv, generate_pdf

logger = logging.getLogger(__name__)

FILES_BUCKET = os.environ.get("FILES_BUCKET", "estimations-files")
PRESIGNED_EXPIRY = 3600  # 1 hora


def handler(event: dict, context: object) -> dict:
    """Endpoint REST para generar y descargar PDF/CSV.

    Recibe estimation_id de pathParameters, format y language del body.
    Obtiene la estimación de DynamoDB, genera el archivo solicitado,
    lo sube a S3 y retorna una URL pre-firmada (expira en 1 hora).

    Args:
        event: Evento de API Gateway REST.
        context: Contexto de Lambda.

    Returns:
        Respuesta HTTP con URL pre-firmada o error.
    """
    try:
        # Extraer parámetros
        path_params = event.get("pathParameters") or {}
        estimation_id = path_params.get("id", "")

        body = event.get("body", "{}")
        if isinstance(body, str):
            body = json.loads(body) if body else {}

        file_format = body.get("format", "pdf").lower()
        language = body.get("language", "es")

        if not estimation_id:
            return _error_response(400, "VALIDATION_ERROR", "estimation_id es requerido")

        if file_format not in ("pdf", "csv"):
            return _error_response(400, "VALIDATION_ERROR", "Formato debe ser 'pdf' o 'csv'")

        # Obtener estimación de DynamoDB
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        estimation = estimation_repo.get_estimation(dynamodb, estimation_id)

        if not estimation:
            return _error_response(404, "NOT_FOUND", "Estimación no encontrada")

        # Generar archivo
        s3_client = boto3.client("s3", region_name="us-east-1")

        if file_format == "pdf":
            file_bytes = generate_pdf(estimation, language)
            content_type = "application/pdf"
            extension = "pdf"
        else:
            csv_content = generate_csv(estimation)
            file_bytes = csv_content.encode("utf-8")
            content_type = "text/csv"
            extension = "csv"

        # Subir a S3 con reintentos
        s3_key = f"exports/{estimation_id}.{extension}"
        uploaded = _upload_to_s3(s3_client, file_bytes, s3_key, content_type)

        if not uploaded:
            # Si falla PDF, ofrecer CSV como alternativa
            if file_format == "pdf":
                return _error_response(
                    500,
                    "SERVICE_ERROR",
                    "Error al generar PDF. Intente con formato CSV como alternativa.",
                )
            return _error_response(500, "SERVICE_ERROR", "Error al subir archivo a S3")

        # Generar URL pre-firmada
        presigned_url = s3_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": FILES_BUCKET, "Key": s3_key},
            ExpiresIn=PRESIGNED_EXPIRY,
        )

        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({
                "file_url": presigned_url,
                "file_key": s3_key,
                "expires_in": PRESIGNED_EXPIRY,
            }),
        }

    except json.JSONDecodeError:
        return _error_response(400, "VALIDATION_ERROR", "Body JSON inválido")
    except Exception as exc:
        logger.exception("Error en pdf_handler: %s", exc)
        return _error_response(500, "INTERNAL_ERROR", "Error interno del servidor")


def _upload_to_s3(
    s3_client, file_bytes: bytes, s3_key: str, content_type: str, max_retries: int = 3
) -> bool:
    """Subir archivo a S3 con reintentos.

    Args:
        s3_client: Cliente boto3 de S3.
        file_bytes: Contenido del archivo.
        s3_key: Clave del objeto en S3.
        content_type: Tipo MIME del archivo.
        max_retries: Número máximo de reintentos.

    Returns:
        True si la subida fue exitosa, False en caso contrario.
    """
    for attempt in range(max_retries):
        try:
            s3_client.put_object(
                Bucket=FILES_BUCKET,
                Key=s3_key,
                Body=file_bytes,
                ContentType=content_type,
            )
            return True
        except Exception as exc:
            logger.warning(
                "Intento %d/%d de subida a S3 falló: %s",
                attempt + 1,
                max_retries,
                exc,
            )
    return False


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
