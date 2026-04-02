"""Modelo de datos para estimaciones de costos."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
import uuid

from src.models.partner import PartnerData


@dataclass
class Estimation:
    """Estimación de costos para un servicio AWS.

    Atributos:
        estimation_id: Identificador único (UUID) de la estimación.
        conversation_id: Conversación asociada.
        user_id: ID del usuario que generó la estimación.
        service: Servicio estimado (amazon_quick/amazon_connect/bedrock_agentcore).
        parameters: Parámetros de entrada específicos del servicio.
        partner_data: Datos del partner y cliente final.
        monthly_cost: Costo mensual estimado.
        annual_cost: Costo anual estimado.
        breakdown: Desglose por componente [{component, unit_price, quantity, monthly_cost}].
        assumptions: Lista de supuestos utilizados en la estimación.
        pricing_date: Fecha de los precios utilizados (ISO8601).
        created_at: Fecha de generación de la estimación (ISO8601).
        language: Idioma de la estimación (es/en/pt/de).
        is_consolidated: Indica si incluye estimaciones externas.
        external_estimations: Datos del JSON externo (si aplica).
        pdf_s3_key: Clave del PDF generado en S3.
    """

    estimation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    conversation_id: str = ""
    user_id: str = ""
    service: str = ""
    parameters: dict[str, Any] = field(default_factory=dict)
    partner_data: PartnerData = field(default_factory=PartnerData)
    monthly_cost: float = 0.0
    annual_cost: float = 0.0
    breakdown: list[dict[str, Any]] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
    pricing_date: str = ""
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    language: str = "es"
    is_consolidated: bool = False
    external_estimations: dict[str, Any] = field(default_factory=dict)
    pdf_s3_key: str = ""
