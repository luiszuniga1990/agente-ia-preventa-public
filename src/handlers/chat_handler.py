"""Handler de mensajes de chat vía WebSocket.

Procesa mensajes $default del WebSocket API Gateway:
extrae datos del body, gestiona conversaciones, detecta idioma,
invoca Bedrock con contexto RAG y envía respuestas al usuario.
Incluye lógica para detectar cuándo el modelo indica que se debe
generar una estimación, consolidar o enviar por email.
"""

import json
import logging
import os
import re

import boto3

from src.models.constants import SUPPORTED_SERVICES
from src.services import conversation_repo, pricing_repo
from src.services.bedrock_client import invoke_model
from src.services.prompt_builder import build_system_prompt
from src.utils.language_detector import detect_language

logger = logging.getLogger(__name__)

# Variables de entorno con valores por defecto
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
CONVERSATIONS_TABLE = os.environ.get("CONVERSATIONS_TABLE", "conversations")
PRICING_TABLE = os.environ.get("PRICING_TABLE", "pricing_cache")


def handler(event: dict, context) -> dict:
    """Procesar mensajes $default del WebSocket.

    Extrae conversation_id y message del body, obtiene o crea la
    conversación, detecta idioma, obtiene precios para RAG, invoca
    Bedrock con historial conversacional, guarda mensajes y envía
    la respuesta al usuario vía API Gateway Management API.

    Args:
        event: Evento de API Gateway WebSocket ($default route).
        context: Contexto de Lambda (no utilizado).

    Returns:
        Respuesta HTTP con statusCode 200 o 500.
    """
    connection_id = event.get("requestContext", {}).get("connectionId", "")
    domain_name = event.get("requestContext", {}).get("domainName", "")
    stage = event.get("requestContext", {}).get("stage", "")

    # Construir endpoint para API Gateway Management API
    endpoint_url = f"https://{domain_name}/{stage}"

    try:
        # Parsear body del mensaje
        body = _parse_body(event)
        if body is None:
            return {"statusCode": 200}

        message = body.get("message", "")
        conversation_id = body.get("conversation_id", "")

        # Ignorar mensajes vacíos
        if not message or not message.strip():
            logger.info("Mensaje vacío recibido, ignorando.")
            return {"statusCode": 200}

        # Inicializar clientes AWS
        dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
        bedrock = boto3.client("bedrock-runtime", region_name=AWS_REGION)
        apigw = boto3.client(
            "apigatewaymanagementapi",
            endpoint_url=endpoint_url,
            region_name=AWS_REGION,
        )

        # Obtener o crear conversación
        conversation = _get_or_create_conversation(
            dynamodb, conversation_id, connection_id
        )

        # Detectar idioma del mensaje
        language = detect_language(message)

        # Obtener precios de todos los servicios para RAG
        pricing_data = _get_all_pricing(dynamodb)

        # Construir system prompt con guardrail + pricing data
        system_prompt = build_system_prompt(language, pricing_data)

        # Construir historial conversacional
        conversation_history = _build_conversation_history(
            conversation.messages
        )

        # Invocar Bedrock con historial
        assistant_response = invoke_model(
            bedrock, message, system_prompt, conversation_history
        )

        # Guardar mensaje del usuario y respuesta del agente
        conversation_repo.add_message(
            dynamodb,
            conversation.conversation_id,
            conversation.user_id,
            "user",
            message,
        )
        conversation_repo.add_message(
            dynamodb,
            conversation.conversation_id,
            conversation.user_id,
            "assistant",
            assistant_response,
        )

        # Verificar si el modelo indica que se debe generar estimación
        estimation_data = _check_estimation_trigger(assistant_response)
        estimation_result = None
        if estimation_data:
            estimation_result = _trigger_estimation_flow(
                dynamodb, bedrock, conversation, estimation_data, language
            )

        # Verificar si el usuario solicita consolidación
        consolidation_result = None
        if _check_consolidation_trigger(message):
            consolidation_result = _trigger_consolidation_flow(
                dynamodb, conversation, message
            )

        # Verificar si se debe enviar email automáticamente
        if _check_email_trigger(message, assistant_response):
            _trigger_email_flow(
                dynamodb, conversation, language
            )

        # Enviar respuesta al usuario vía WebSocket
        response_payload = {
            "conversation_id": conversation.conversation_id,
            "response": assistant_response,
            "detected_language": language,
        }
        if estimation_result:
            response_payload["estimation_id"] = estimation_result.get(
                "estimation_id", ""
            )
        if consolidation_result:
            response_payload["consolidated"] = True

        _post_to_connection(apigw, connection_id, response_payload)

        return {"statusCode": 200}

    except Exception as exc:
        logger.error("Error procesando mensaje: %s", str(exc))
        _send_error_to_client(
            connection_id, endpoint_url, str(exc)
        )
        return {"statusCode": 500}


def _parse_body(event: dict) -> dict | None:
    """Parsear el body del evento WebSocket como JSON.

    Args:
        event: Evento de API Gateway WebSocket.

    Returns:
        Diccionario con los datos del body, o None si el body es inválido.
    """
    raw_body = event.get("body", "")
    if not raw_body:
        logger.warning("Body vacío en el evento WebSocket.")
        return None

    try:
        return json.loads(raw_body)
    except (json.JSONDecodeError, TypeError) as exc:
        logger.warning("Body no es JSON válido: %s", exc)
        return None


def _get_or_create_conversation(
    dynamodb, conversation_id: str, user_id: str
):
    """Obtener conversación existente o crear una nueva.

    Args:
        dynamodb: Recurso boto3 de DynamoDB.
        conversation_id: ID de la conversación (vacío para crear nueva).
        user_id: ID del usuario (connectionId como fallback).

    Returns:
        Objeto Conversation.
    """
    if conversation_id:
        conversation = conversation_repo.get_conversation(
            dynamodb, conversation_id
        )
        if conversation:
            return conversation

    # Crear nueva conversación
    return conversation_repo.create_conversation(
        dynamodb, user_id, "es"
    )


def _get_all_pricing(dynamodb) -> list:
    """Obtener precios de todos los servicios soportados para RAG.

    Args:
        dynamodb: Recurso boto3 de DynamoDB.

    Returns:
        Lista combinada de PricingEntry de todos los servicios.
    """
    all_pricing = []
    for service_id in SUPPORTED_SERVICES:
        entries = pricing_repo.get_pricing(dynamodb, service_id)
        all_pricing.extend(entries)
    return all_pricing


def _build_conversation_history(messages: list[dict]) -> list[dict]:
    """Construir historial conversacional para Bedrock.

    Transforma la lista de mensajes almacenados al formato esperado
    por bedrock_client.invoke_model.

    Args:
        messages: Lista de mensajes [{role, content, timestamp}].

    Returns:
        Lista de mensajes [{role, content}] para Bedrock.
    """
    history = []
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if content:
            history.append({"role": role, "content": content})
    return history


def _post_to_connection(
    apigw_client, connection_id: str, payload: dict
) -> None:
    """Enviar datos al cliente vía API Gateway Management API.

    Args:
        apigw_client: Cliente boto3 de apigatewaymanagementapi.
        connection_id: ID de la conexión WebSocket.
        payload: Datos a enviar como JSON.
    """
    try:
        apigw_client.post_to_connection(
            ConnectionId=connection_id,
            Data=json.dumps(payload).encode("utf-8"),
        )
    except apigw_client.exceptions.GoneException:
        logger.warning(
            "Conexión perdida al enviar respuesta. connectionId=%s",
            connection_id,
        )
    except Exception as exc:
        logger.error(
            "Error enviando respuesta al cliente: %s", str(exc)
        )


def _send_error_to_client(
    connection_id: str, endpoint_url: str, error_message: str
) -> None:
    """Enviar mensaje de error al cliente vía WebSocket.

    Intenta enviar un mensaje de error amigable. Si falla (conexión
    perdida), simplemente registra el error en logs.

    Args:
        connection_id: ID de la conexión WebSocket.
        endpoint_url: URL del endpoint de API Gateway Management API.
        error_message: Mensaje de error a enviar.
    """
    if not connection_id or not endpoint_url:
        return

    try:
        apigw = boto3.client(
            "apigatewaymanagementapi",
            endpoint_url=endpoint_url,
            region_name=AWS_REGION,
        )
        error_payload = {
            "type": "error",
            "error": {
                "code": "INTERNAL_ERROR",
                "message": (
                    "Ha ocurrido un error procesando su mensaje. "
                    "Por favor, intente de nuevo."
                ),
            },
        }
        apigw.post_to_connection(
            ConnectionId=connection_id,
            Data=json.dumps(error_payload).encode("utf-8"),
        )
    except Exception as exc:
        logger.error(
            "No se pudo enviar error al cliente: %s", str(exc)
        )


def _check_estimation_trigger(response_text: str) -> dict | None:
    """Verificar si la respuesta del modelo contiene datos para generar estimación.

    Busca un bloque JSON en la respuesta que contenga los campos necesarios
    para generar una estimación (service, parameters, partner_data).

    Args:
        response_text: Texto de respuesta del modelo.

    Returns:
        Diccionario con datos de estimación si se detecta, None en caso contrario.
    """
    if not response_text:
        return None

    # Buscar bloque JSON delimitado por ```json ... ```
    json_data = _extract_json_from_response(response_text)
    if json_data is None:
        return None

    # Verificar que tiene los campos mínimos para una estimación
    required_keys = {"service", "parameters", "partner_data"}
    if not required_keys.issubset(json_data.keys()):
        return None

    # Verificar que el servicio es soportado
    service = json_data.get("service", "")
    if service not in SUPPORTED_SERVICES:
        return None

    # Verificar que partner_data tiene campos mínimos
    partner = json_data.get("partner_data", {})
    if not isinstance(partner, dict):
        return None

    partner_fields = {"partner_name", "partner_email", "region", "end_customer"}
    if not partner_fields.issubset(partner.keys()):
        return None

    return json_data


def _extract_json_from_response(text: str) -> dict | None:
    """Extraer bloque JSON de la respuesta del modelo.

    Args:
        text: Texto que puede contener un bloque JSON.

    Returns:
        Diccionario parseado o None.
    """
    start_marker = "```json"
    end_marker = "```"

    start_idx = text.find(start_marker)
    if start_idx == -1:
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


def _trigger_estimation_flow(
    dynamodb, bedrock, conversation, estimation_data: dict, language: str
) -> dict | None:
    """Disparar flujo de generación de estimación.

    Invoca estimation_service con los datos extraídos de la respuesta
    del modelo.

    Args:
        dynamodb: Recurso boto3 de DynamoDB.
        bedrock: Cliente boto3 de bedrock-runtime.
        conversation: Objeto Conversation activa.
        estimation_data: Datos de estimación extraídos del modelo.
        language: Código de idioma detectado.

    Returns:
        Diccionario con estimation_id si fue exitoso, None si falló.
    """
    try:
        from src.services.estimation_service import generate_estimation

        estimation = generate_estimation(
            dynamodb=dynamodb,
            bedrock=bedrock,
            user_id=conversation.user_id,
            conversation_id=conversation.conversation_id,
            service=estimation_data["service"],
            parameters=estimation_data.get("parameters", {}),
            partner_data=estimation_data.get("partner_data", {}),
            language=language,
        )
        logger.info(
            "Estimación generada: %s para conversación %s",
            estimation.estimation_id,
            conversation.conversation_id,
        )
        return {"estimation_id": estimation.estimation_id}
    except (ValueError, RuntimeError) as exc:
        logger.warning("Error generando estimación desde chat: %s", exc)
        return None
    except Exception as exc:
        logger.error("Error inesperado en flujo de estimación: %s", exc)
        return None


def _check_consolidation_trigger(message: str) -> bool:
    """Verificar si el mensaje del usuario solicita consolidación.

    Busca palabras clave que indiquen que el usuario quiere consolidar
    estimaciones externas.

    Args:
        message: Mensaje del usuario.

    Returns:
        True si se detecta solicitud de consolidación.
    """
    if not message:
        return False

    consolidation_keywords = [
        "consolidar", "consolidate", "konsolidieren",
        "combinar", "combine",
        "json externo", "external json",
        "estimación externa", "external estimation",
    ]
    message_lower = message.lower()
    return any(kw in message_lower for kw in consolidation_keywords)


def _trigger_consolidation_flow(
    dynamodb, conversation, message: str
) -> dict | None:
    """Disparar flujo de consolidación de estimaciones.

    Busca datos JSON en el mensaje del usuario y consolida con la
    última estimación de la conversación.

    Args:
        dynamodb: Recurso boto3 de DynamoDB.
        conversation: Objeto Conversation activa.
        message: Mensaje del usuario que puede contener JSON.

    Returns:
        Diccionario con resultado de consolidación o None.
    """
    try:
        from src.services import consolidation_service, estimation_repo

        # Buscar la última estimación del usuario
        estimations = estimation_repo.list_estimations(
            dynamodb, conversation.user_id
        )
        if not estimations:
            logger.info("No hay estimaciones para consolidar.")
            return None

        latest_estimation = estimations[0]

        # Intentar extraer JSON del mensaje
        json_data = _extract_json_from_response(message)
        if json_data is None:
            return None

        consolidated = consolidation_service.consolidate(
            dynamodb, latest_estimation.estimation_id, json_data
        )
        logger.info(
            "Consolidación exitosa: %s", consolidated.estimation_id
        )
        return {"estimation_id": consolidated.estimation_id, "consolidated": True}
    except Exception as exc:
        logger.warning("Error en flujo de consolidación: %s", exc)
        return None


def _check_email_trigger(message: str, response_text: str) -> bool:
    """Verificar si se debe enviar email automáticamente.

    Detecta si el usuario solicita envío por correo o si el modelo
    sugiere enviar la estimación.

    Args:
        message: Mensaje del usuario.
        response_text: Respuesta del modelo.

    Returns:
        True si se debe disparar envío de email.
    """
    if not message:
        return False

    email_keywords = [
        "enviar por correo", "enviar email", "send email",
        "send by email", "per e-mail senden",
        "enviar por email", "mandar correo",
        "enviar estimación", "send estimation",
    ]
    message_lower = message.lower()
    return any(kw in message_lower for kw in email_keywords)


def _trigger_email_flow(
    dynamodb, conversation, language: str
) -> None:
    """Disparar flujo de envío de email con la última estimación.

    Genera PDF y envía por correo a la dirección del partner.

    Args:
        dynamodb: Recurso boto3 de DynamoDB.
        conversation: Objeto Conversation activa.
        language: Código de idioma.
    """
    try:
        from src.services import estimation_repo
        from src.services.email_service import send_estimation_email
        from src.services.pdf_generator import generate_pdf

        # Obtener última estimación del usuario
        estimations = estimation_repo.list_estimations(
            dynamodb, conversation.user_id
        )
        if not estimations:
            logger.info("No hay estimaciones para enviar por email.")
            return

        latest = estimations[0]
        recipient = latest.partner_data.partner_email
        if not recipient:
            logger.warning("No hay email del partner para enviar.")
            return

        # Generar PDF
        pdf_bytes = generate_pdf(latest, language)

        # Enviar email
        ses_client = boto3.client("ses", region_name=AWS_REGION)
        result = send_estimation_email(
            ses_client, latest, recipient, pdf_bytes, language
        )
        logger.info("Email enviado: %s", result.get("message_id", ""))
    except Exception as exc:
        logger.error("Error en flujo de email automático: %s", exc)


def _check_recalculation_trigger(
    message: str, conversation_messages: list[dict]
) -> bool:
    """Verificar si el usuario solicita recálculo de estimación.

    Detecta si el usuario modifica parámetros en la misma sesión
    donde ya se generó una estimación.

    Args:
        message: Mensaje actual del usuario.
        conversation_messages: Historial de mensajes de la conversación.

    Returns:
        True si se detecta solicitud de recálculo.
    """
    if not message:
        return False

    recalc_keywords = [
        "recalcular", "recalculate", "neu berechnen",
        "modificar", "modify", "cambiar", "change",
        "actualizar parámetros", "update parameters",
        "ajustar", "adjust",
    ]
    message_lower = message.lower()
    has_keyword = any(kw in message_lower for kw in recalc_keywords)

    if not has_keyword:
        return False

    # Verificar que ya hubo una estimación en la conversación
    for msg in conversation_messages:
        content = msg.get("content", "")
        if "estimation_id" in content or "estimación" in content.lower():
            return True

    return False
