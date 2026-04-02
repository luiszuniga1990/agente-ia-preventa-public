"""Repositorio de estimaciones en DynamoDB.

Gestiona operaciones CRUD sobre la tabla `estimations`.
Esquema: PK=estimation_id, GSI user_id-index (PK=user_id, SK=created_at).
"""

from dataclasses import asdict
from decimal import Decimal

from src.models import Estimation, PartnerData


def _convert_floats(obj):
    """Convertir floats a Decimal recursivamente para compatibilidad con DynamoDB.

    Args:
        obj: Objeto a convertir (dict, list, float, o cualquier otro tipo).

    Returns:
        Objeto con floats convertidos a Decimal.
    """
    if isinstance(obj, float):
        return Decimal(str(obj))
    if isinstance(obj, dict):
        return {k: _convert_floats(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_convert_floats(i) for i in obj]
    return obj


def save_estimation(dynamodb, estimation: Estimation) -> str:
    """Guardar estimación en DynamoDB y retornar estimation_id.

    Args:
        dynamodb: Recurso boto3 de DynamoDB.
        estimation: Objeto Estimation a guardar.

    Returns:
        estimation_id de la estimación guardada.
    """
    table = dynamodb.Table("estimations")
    item = {
        "estimation_id": estimation.estimation_id,
        "conversation_id": estimation.conversation_id,
        "user_id": estimation.user_id,
        "service": estimation.service,
        "parameters": _convert_floats(estimation.parameters),
        "partner_data": asdict(estimation.partner_data),
        "monthly_cost": Decimal(str(estimation.monthly_cost)),
        "annual_cost": Decimal(str(estimation.annual_cost)),
        "breakdown": _convert_floats(estimation.breakdown),
        "assumptions": estimation.assumptions,
        "pricing_date": estimation.pricing_date,
        "created_at": estimation.created_at,
        "language": estimation.language,
        "is_consolidated": estimation.is_consolidated,
        "external_estimations": _convert_floats(estimation.external_estimations),
        "pdf_s3_key": estimation.pdf_s3_key,
    }
    table.put_item(Item=item)
    return estimation.estimation_id


def get_estimation(dynamodb, estimation_id: str) -> Estimation | None:
    """Obtener estimación por estimation_id (PK).

    Args:
        dynamodb: Recurso boto3 de DynamoDB.
        estimation_id: ID único de la estimación.

    Returns:
        Objeto Estimation o None si no existe.
    """
    table = dynamodb.Table("estimations")
    response = table.get_item(Key={"estimation_id": estimation_id})
    item = response.get("Item")
    if not item:
        return None
    return _item_to_estimation(item)


def list_estimations(dynamodb, user_id: str) -> list[Estimation]:
    """Listar estimaciones del usuario usando GSI user_id-index.

    Args:
        dynamodb: Recurso boto3 de DynamoDB.
        user_id: ID del usuario.

    Returns:
        Lista de estimaciones del usuario ordenadas por fecha descendente.
    """
    table = dynamodb.Table("estimations")
    response = table.query(
        IndexName="user_id-index",
        KeyConditionExpression="user_id = :uid",
        ExpressionAttributeValues={":uid": user_id},
        ScanIndexForward=False,
    )
    items = response.get("Items", [])
    return [_item_to_estimation(item) for item in items]


def _convert_decimals(obj):
    """Convertir Decimal a float recursivamente al leer de DynamoDB.

    Args:
        obj: Objeto a convertir.

    Returns:
        Objeto con Decimals convertidos a float.
    """
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, dict):
        return {k: _convert_decimals(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_convert_decimals(i) for i in obj]
    return obj


def _item_to_estimation(item: dict) -> Estimation:
    """Convertir un item de DynamoDB a un objeto Estimation.

    Args:
        item: Diccionario con los datos del item.

    Returns:
        Objeto Estimation.
    """
    partner_dict = item.get("partner_data", {})
    partner = PartnerData(
        partner_name=partner_dict.get("partner_name", ""),
        partner_email=partner_dict.get("partner_email", ""),
        region=partner_dict.get("region", ""),
        end_customer=partner_dict.get("end_customer", ""),
    )
    return Estimation(
        estimation_id=item.get("estimation_id", ""),
        conversation_id=item.get("conversation_id", ""),
        user_id=item.get("user_id", ""),
        service=item.get("service", ""),
        parameters=_convert_decimals(item.get("parameters", {})),
        partner_data=partner,
        monthly_cost=float(item.get("monthly_cost", 0)),
        annual_cost=float(item.get("annual_cost", 0)),
        breakdown=_convert_decimals(item.get("breakdown", [])),
        assumptions=item.get("assumptions", []),
        pricing_date=item.get("pricing_date", ""),
        created_at=item.get("created_at", ""),
        language=item.get("language", "es"),
        is_consolidated=item.get("is_consolidated", False),
        external_estimations=_convert_decimals(item.get("external_estimations", {})),
        pdf_s3_key=item.get("pdf_s3_key", ""),
    )
