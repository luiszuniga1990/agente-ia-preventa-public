"""Handler para actualización diaria de precios vía EventBridge.

Invocado por EventBridge (cron diario). Para cada servicio soportado,
obtiene precios actualizados desde las URLs oficiales y actualiza
la caché en DynamoDB.
"""

import logging
import os
from datetime import datetime, timezone

import boto3

from src.models.constants import SUPPORTED_SERVICES
from src.services import pricing_repo
from src.services.pricing_scraper import PRICING_URLS, fetch_pricing

logger = logging.getLogger(__name__)

AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")


def handler(event: dict, context: object) -> dict:
    """Actualizar precios de todos los servicios soportados.

    Para cada servicio: invoca fetch_pricing, actualiza pricing_repo
    con datos nuevos y timestamp. Si falla el fetch de una URL,
    mantiene caché existente y registra warning. Si todas fallan,
    mantiene caché completo y registra error crítico.

    Args:
        event: Evento de EventBridge (Scheduled Event).
        context: Contexto de Lambda.

    Returns:
        Resumen con servicios actualizados y errores.
    """
    dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)

    updated_services: list[str] = []
    errors: list[str] = []

    for service_id in SUPPORTED_SERVICES:
        url = PRICING_URLS.get(service_id, "")
        if not url:
            error_msg = f"No hay URL de pricing para {service_id}"
            logger.warning(error_msg)
            errors.append(error_msg)
            continue

        try:
            pricing_data = fetch_pricing(service_id, url)

            if not pricing_data:
                logger.warning(
                    "No se obtuvieron datos de precios para %s desde %s",
                    service_id, url,
                )
                errors.append(f"Sin datos de precios para {service_id}")
                continue

            # Actualizar cada componente en la caché
            for entry in pricing_data:
                component = entry.get("unit", "general")
                pricing_repo.update_pricing(
                    dynamodb, service_id, component, entry
                )

            updated_services.append(service_id)
            logger.info(
                "Precios actualizados para %s: %d componentes",
                service_id, len(pricing_data),
            )

        except (ConnectionError, ValueError) as exc:
            error_msg = f"Error actualizando {service_id}: {exc}"
            logger.warning(error_msg)
            errors.append(error_msg)
        except Exception as exc:
            error_msg = f"Error inesperado actualizando {service_id}: {exc}"
            logger.error(error_msg)
            errors.append(error_msg)

    # Si todas las URLs fallaron, registrar error crítico
    if not updated_services and errors:
        logger.critical(
            "TODAS las URLs de pricing fallaron. "
            "Manteniendo caché existente. Errores: %s",
            "; ".join(errors),
        )

    timestamp = datetime.now(timezone.utc).isoformat()

    return {
        "services_updated": updated_services,
        "timestamp": timestamp,
        "errors": errors,
        "total_updated": len(updated_services),
        "total_errors": len(errors),
    }
