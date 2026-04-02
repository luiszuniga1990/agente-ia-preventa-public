"""Servicio de generación de estimaciones de costos.

Orquesta la validación de datos, obtención de precios, invocación a Bedrock
y persistencia de estimaciones en DynamoDB.
"""

import json
import logging
import uuid
from datetime import datetime, timezone

from src.models.estimation import Estimation
from src.models.partner import PartnerData
from src.services import bedrock_client as bedrock_mod
from src.services import estimation_repo, pricing_repo
from src.services.prompt_builder import build_estimation_prompt, build_system_prompt
from src.utils.validators import validate_email, validate_partner_data, validate_service

logger = logging.getLogger(__name__)

# Disclaimer incluido en toda estimación
DISCLAIMER = (
    "Los costos son aproximados y están sujetos a cambios "
    "según los precios vigentes del proveedor."
)


def generate_estimation(
    dynamodb,
    bedrock,
    user_id: str,
    conversation_id: str,
    service: str,
    parameters: dict,
    partner_data: dict,
    language: str = "es",
) -> Estimation:
    """Orquestar la generación completa de una estimación de costos.

    Valida datos de entrada, obtiene precios actualizados, invoca Bedrock
    para generar la estimación y la persiste en DynamoDB.

    Args:
        dynamodb: Recurso boto3 de DynamoDB.
        bedrock: Cliente boto3 de bedrock-runtime.
        user_id: ID del usuario que solicita la estimación.
        conversation_id: ID de la conversación asociada.
        service: Servicio a estimar (amazon_quick/amazon_connect/bedrock_agentcore).
        parameters: Parámetros específicos del servicio.
        partner_data: Diccionario con datos del partner
            (partner_name, partner_email, region, end_customer).
        language: Código ISO del idioma (es/en/pt/de).

    Returns:
        Objeto Estimation completo con todos los campos.

    Raises:
        ValueError: Si los datos del partner son inválidos, el servicio no está
            soportado o el email tiene formato incorrecto.
        RuntimeError: Si Bedrock falla (propagado desde bedrock_client).
    """
    # 1. Validar servicio
    if not validate_service(service):
        raise ValueError(
            f"Servicio no soportado: '{service}'. "
            "Servicios válidos: amazon_quick, amazon_connect, bedrock_agentcore."
        )

    # 2. Validar datos del partner
    is_valid, missing = validate_partner_data(partner_data)
    if not is_valid:
        raise ValueError(
            f"Datos del partner incompletos. Campos faltantes: {', '.join(missing)}"
        )

    # 3. Validar email del partner
    email = partner_data.get("partner_email", "")
    if not validate_email(email):
        raise ValueError(
            f"Formato de correo electrónico inválido: '{email}'"
        )

    # 4. Obtener precios actualizados
    pricing_data = pricing_repo.get_pricing(dynamodb, service)
    pricing_date = pricing_repo.get_last_updated(dynamodb, service)
    if not pricing_date:
        pricing_date = datetime.now(timezone.utc).isoformat()

    # 5. Construir prompts e invocar Bedrock
    system_prompt = build_system_prompt(language, pricing_data)
    estimation_prompt = build_estimation_prompt(
        service, parameters, pricing_data, language
    )

    # Instruir al modelo a devolver JSON estructurado
    json_instruction = _build_json_instruction()
    full_prompt = f"{estimation_prompt}\n\n{json_instruction}"

    model_response = bedrock_mod.invoke_model(
        bedrock, full_prompt, system_prompt
    )

    # 6. Parsear respuesta del modelo
    monthly_cost, annual_cost, breakdown, assumptions = _parse_model_response(
        model_response
    )

    # 7. Asegurar disclaimer en assumptions
    if not any("aproximados" in a.lower() or "approximate" in a.lower() for a in assumptions):
        assumptions.append(DISCLAIMER)

    # 8. Construir objeto Estimation
    partner = PartnerData(
        partner_name=partner_data["partner_name"],
        partner_email=partner_data["partner_email"],
        region=partner_data["region"],
        end_customer=partner_data["end_customer"],
    )

    estimation = Estimation(
        estimation_id=str(uuid.uuid4()),
        conversation_id=conversation_id,
        user_id=user_id,
        service=service,
        parameters=parameters,
        partner_data=partner,
        monthly_cost=monthly_cost,
        annual_cost=annual_cost,
        breakdown=breakdown,
        assumptions=assumptions,
        pricing_date=pricing_date,
        language=language,
    )

    # 9. Guardar en DynamoDB
    estimation_repo.save_estimation(dynamodb, estimation)

    return estimation


def _build_json_instruction() -> str:
    """Construir instrucción para que el modelo devuelva JSON estructurado.

    Returns:
        Texto con la instrucción de formato JSON.
    """
    return """IMPORTANT: In addition to the human-readable response above, include at the END of your response a JSON block delimited by ```json and ``` with the following structure:
```json
{
    "monthly_cost": <number>,
    "annual_cost": <number>,
    "breakdown": [
        {
            "component": "<string>",
            "unit_price": <number>,
            "quantity": <number>,
            "monthly_cost": <number>
        }
    ],
    "assumptions": ["<string>", "<string>"]
}
```
Ensure the JSON is valid and the numbers are consistent with your calculation."""


def _parse_model_response(
    response: str,
) -> tuple[float, float, list[dict], list[str]]:
    """Parsear la respuesta del modelo para extraer datos de estimación.

    Intenta extraer un bloque JSON de la respuesta. Si no se encuentra
    o el parsing falla, crea una estimación básica con la respuesta cruda.

    Args:
        response: Texto de respuesta del modelo.

    Returns:
        Tupla (monthly_cost, annual_cost, breakdown, assumptions).
    """
    # Intentar extraer JSON de la respuesta
    json_data = _extract_json_block(response)
    if json_data:
        try:
            monthly_cost = float(json_data.get("monthly_cost", 0))
            annual_cost = float(json_data.get("annual_cost", 0))
            breakdown = json_data.get("breakdown", [])
            assumptions = json_data.get("assumptions", [])

            # Validar tipos
            if not isinstance(breakdown, list):
                breakdown = []
            if not isinstance(assumptions, list):
                assumptions = []

            # Asegurar que breakdown tiene la estructura correcta
            validated_breakdown = []
            for item in breakdown:
                if isinstance(item, dict):
                    validated_breakdown.append({
                        "component": str(item.get("component", "")),
                        "unit_price": float(item.get("unit_price", 0)),
                        "quantity": float(item.get("quantity", 0)),
                        "monthly_cost": float(item.get("monthly_cost", 0)),
                    })

            # Asegurar que assumptions son strings
            validated_assumptions = [str(a) for a in assumptions if a]

            return (
                monthly_cost,
                annual_cost,
                validated_breakdown if validated_breakdown else [
                    {"component": "Total", "unit_price": monthly_cost, "quantity": 1, "monthly_cost": monthly_cost}
                ],
                validated_assumptions if validated_assumptions else [response[:500]],
            )
        except (ValueError, TypeError, KeyError) as exc:
            logger.warning("Error parseando JSON de respuesta: %s", exc)

    # Fallback: crear estimación básica con la respuesta cruda
    logger.info("No se encontró JSON válido en la respuesta, usando fallback.")
    return (
        0.0,
        0.0,
        [{"component": "Estimación pendiente de cálculo", "unit_price": 0, "quantity": 1, "monthly_cost": 0}],
        [response[:500] if response else "Estimación generada sin datos estructurados."],
    )


def _extract_json_block(text: str) -> dict | None:
    """Extraer bloque JSON delimitado por ```json ... ``` de un texto.

    Args:
        text: Texto que puede contener un bloque JSON.

    Returns:
        Diccionario parseado o None si no se encuentra JSON válido.
    """
    # Buscar bloque ```json ... ```
    start_marker = "```json"
    end_marker = "```"

    start_idx = text.find(start_marker)
    if start_idx == -1:
        # Intentar parsear toda la respuesta como JSON
        try:
            data = json.loads(text.strip())
            if isinstance(data, dict):
                return data
        except (json.JSONDecodeError, ValueError):
            pass
        return None

    json_start = start_idx + len(start_marker)
    end_idx = text.find(end_marker, json_start)
    if end_idx == -1:
        return None

    json_str = text[json_start:end_idx].strip()
    try:
        data = json.loads(json_str)
        if isinstance(data, dict):
            return data
    except (json.JSONDecodeError, ValueError):
        pass

    return None
