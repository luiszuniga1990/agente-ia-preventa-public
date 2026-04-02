"""Modelo de datos para entradas de pricing."""

from dataclasses import dataclass


@dataclass
class PricingEntry:
    """Entrada de precio para un componente de un servicio.

    Atributos:
        service_id: Identificador del servicio (amazon_quick/amazon_connect/bedrock_agentcore).
        component: Nombre del componente o tier de pricing.
        unit_price: Precio unitario.
        unit: Unidad de medida (user/month, minute, invocation, etc.).
        last_updated: Fecha de última actualización exitosa (ISO8601).
    """

    service_id: str = ""
    component: str = ""
    unit_price: float = 0.0
    unit: str = ""
    last_updated: str = ""
