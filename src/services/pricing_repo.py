"""Repositorio de caché de precios en DynamoDB.

Gestiona operaciones sobre la tabla `pricing_cache`.
Esquema: PK=service_id, SK=component.
"""

from datetime import datetime, timezone

from src.models import PricingEntry


def get_pricing(dynamodb, service_id: str) -> list[PricingEntry]:
    """Obtener todos los precios de un servicio desde la tabla pricing_cache.

    Args:
        dynamodb: Recurso boto3 de DynamoDB.
        service_id: Identificador del servicio (amazon_quick/amazon_connect/bedrock_agentcore).

    Returns:
        Lista de PricingEntry para el servicio.
    """
    table = dynamodb.Table("pricing_cache")
    response = table.query(
        KeyConditionExpression="service_id = :sid",
        ExpressionAttributeValues={":sid": service_id},
    )
    items = response.get("Items", [])
    return [_item_to_pricing_entry(item) for item in items]


def update_pricing(
    dynamodb, service_id: str, component: str, data: dict
) -> None:
    """Actualizar o crear entrada de precio con timestamp actual.

    Args:
        dynamodb: Recurso boto3 de DynamoDB.
        service_id: Identificador del servicio.
        component: Nombre del componente o tier.
        data: Diccionario con datos del precio (unit_price, unit, tier, currency, source_url, raw_data).
    """
    table = dynamodb.Table("pricing_cache")
    now = datetime.now(timezone.utc).isoformat()
    item = {
        "service_id": service_id,
        "component": component,
        "unit_price": str(data.get("unit_price", 0)),
        "unit": data.get("unit", ""),
        "tier": data.get("tier", ""),
        "currency": data.get("currency", "USD"),
        "source_url": data.get("source_url", ""),
        "last_updated": now,
        "raw_data": data.get("raw_data", {}),
    }
    table.put_item(Item=item)


def get_last_updated(dynamodb, service_id: str) -> str:
    """Obtener fecha de última actualización de un servicio.

    Consulta todos los componentes del servicio y retorna el timestamp
    más reciente.

    Args:
        dynamodb: Recurso boto3 de DynamoDB.
        service_id: Identificador del servicio.

    Returns:
        Fecha ISO8601 de la última actualización, o cadena vacía si no hay datos.
    """
    table = dynamodb.Table("pricing_cache")
    response = table.query(
        KeyConditionExpression="service_id = :sid",
        ExpressionAttributeValues={":sid": service_id},
    )
    items = response.get("Items", [])
    if not items:
        return ""
    timestamps = [item.get("last_updated", "") for item in items if item.get("last_updated")]
    if not timestamps:
        return ""
    return max(timestamps)


def _item_to_pricing_entry(item: dict) -> PricingEntry:
    """Convertir un item de DynamoDB a un objeto PricingEntry.

    Args:
        item: Diccionario con los datos del item.

    Returns:
        Objeto PricingEntry.
    """
    return PricingEntry(
        service_id=item.get("service_id", ""),
        component=item.get("component", ""),
        unit_price=float(item.get("unit_price", 0)),
        unit=item.get("unit", ""),
        last_updated=item.get("last_updated", ""),
    )
