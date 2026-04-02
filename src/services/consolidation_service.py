"""Servicio de consolidación de estimaciones internas con datos externos.

Permite combinar una estimación generada por el agente con estimaciones
externas proporcionadas en formato JSON, sin modificar los datos externos.
"""

import logging
import uuid
from datetime import datetime, timezone

from src.models.estimation import Estimation
from src.services import estimation_repo
from src.utils.validators import validate_json_file

logger = logging.getLogger(__name__)


def consolidate(
    dynamodb,
    estimation_id: str,
    external_json: dict,
) -> Estimation:
    """Consolidar estimación interna con datos externos.

    Obtiene la estimación existente de DynamoDB, valida el JSON externo,
    toma los datos externos tal cual (sin modificar ni recalcular),
    calcula totales consolidados y guarda una nueva estimación consolidada.

    Args:
        dynamodb: Recurso boto3 de DynamoDB.
        estimation_id: ID de la estimación interna existente.
        external_json: Diccionario con datos de estimaciones externas.

    Returns:
        Nueva Estimation consolidada con is_consolidated=True.

    Raises:
        ValueError: Si el JSON externo es inválido o la estimación no existe.
    """
    # 1. Obtener estimación existente
    existing = estimation_repo.get_estimation(dynamodb, estimation_id)
    if not existing:
        raise ValueError(f"Estimación no encontrada: {estimation_id}")

    # 2. Validar JSON externo (como string para validate_json_file)
    import json
    json_str = json.dumps(external_json)
    is_valid, result = validate_json_file(json_str)
    if not is_valid:
        raise ValueError(f"JSON externo inválido: {result}")

    # 3. Calcular totales consolidados
    ext_services = external_json.get("external_services", [])
    ext_monthly_total = sum(
        float(svc.get("monthly_cost", 0)) for svc in ext_services
    )
    ext_annual_total = sum(
        float(svc.get("annual_cost", 0)) for svc in ext_services
    )

    total_monthly = existing.monthly_cost + ext_monthly_total
    total_annual = existing.annual_cost + ext_annual_total

    # 4. Crear nueva estimación consolidada
    consolidated = Estimation(
        estimation_id=str(uuid.uuid4()),
        conversation_id=existing.conversation_id,
        user_id=existing.user_id,
        service=existing.service,
        parameters=existing.parameters,
        partner_data=existing.partner_data,
        monthly_cost=total_monthly,
        annual_cost=total_annual,
        breakdown=existing.breakdown,
        assumptions=existing.assumptions,
        pricing_date=existing.pricing_date,
        created_at=datetime.now(timezone.utc).isoformat(),
        language=existing.language,
        is_consolidated=True,
        external_estimations=external_json,
        pdf_s3_key="",
    )

    # 5. Guardar en DynamoDB
    estimation_repo.save_estimation(dynamodb, consolidated)

    return consolidated
