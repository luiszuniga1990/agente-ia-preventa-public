"""Cliente para invocación de Amazon Bedrock (Nova Pro).

Encapsula la comunicación con Amazon Bedrock Runtime usando la API Converse,
con retry automático, manejo de errores y mensajes amigables.
"""

import logging
import time

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

# Configuración del modelo
MODEL_ID = "amazon.nova-pro-v1:0"
MAX_TOKENS = 4096
TEMPERATURE = 0.3
TIMEOUT_SECONDS = 30

# Configuración de retry
MAX_RETRIES = 3
BASE_BACKOFF_SECONDS = 1.0

# Mensaje de error amigable por defecto
DEFAULT_ERROR_MESSAGE = (
    "El servicio está temporalmente fuera de servicio. "
    "Por favor, intente de nuevo más tarde."
)


def invoke_model(
    bedrock_client,
    prompt: str,
    system_prompt: str = "",
    conversation_history: list[dict] | None = None,
) -> str:
    """Invocar Amazon Nova Pro vía Bedrock Runtime con la API Converse.

    Construye la lista de mensajes a partir del historial conversacional
    y el prompt actual, invoca el modelo con retry y backoff exponencial,
    y retorna la respuesta como texto.

    Args:
        bedrock_client: Cliente boto3 de bedrock-runtime.
        prompt: Mensaje del usuario actual.
        system_prompt: Prompt de sistema con instrucciones y contexto RAG.
        conversation_history: Historial de mensajes previos
            [{role: "user"|"assistant", content: "..."}].

    Returns:
        Texto de respuesta del modelo.

    Raises:
        RuntimeError: Si Bedrock falla después de todos los reintentos,
            con un mensaje amigable sin detalles técnicos.
    """
    messages = _build_messages(prompt, conversation_history)
    system = _build_system(system_prompt)
    inference_config = {
        "maxTokens": MAX_TOKENS,
        "temperature": TEMPERATURE,
    }

    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            kwargs = {
                "modelId": MODEL_ID,
                "messages": messages,
                "inferenceConfig": inference_config,
            }
            if system:
                kwargs["system"] = system

            response = bedrock_client.converse(**kwargs)
            return _extract_text(response)

        except ClientError as exc:
            error_code = exc.response.get("Error", {}).get("Code", "")
            last_error = exc
            logger.warning(
                "Bedrock invocation attempt %d/%d failed: %s - %s",
                attempt,
                MAX_RETRIES,
                error_code,
                str(exc),
            )

            if error_code == "ThrottlingException" and attempt < MAX_RETRIES:
                _wait_backoff(attempt)
                continue

            if error_code in (
                "ServiceUnavailableException",
                "InternalServerException",
            ) and attempt < MAX_RETRIES:
                _wait_backoff(attempt)
                continue

            break

        except Exception as exc:
            last_error = exc
            logger.error(
                "Error inesperado invocando Bedrock (intento %d/%d): %s",
                attempt,
                MAX_RETRIES,
                str(exc),
            )
            if attempt < MAX_RETRIES:
                _wait_backoff(attempt)
                continue
            break

    logger.error("Bedrock falló después de %d intentos: %s", MAX_RETRIES, last_error)
    raise RuntimeError(DEFAULT_ERROR_MESSAGE)


def _build_messages(
    prompt: str, conversation_history: list[dict] | None
) -> list[dict]:
    """Construir lista de mensajes para la API Converse.

    Args:
        prompt: Mensaje actual del usuario.
        conversation_history: Historial previo de mensajes.

    Returns:
        Lista de mensajes en formato Converse API.
    """
    messages: list[dict] = []

    if conversation_history:
        for msg in conversation_history:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            messages.append({
                "role": role,
                "content": [{"text": content}],
            })

    messages.append({
        "role": "user",
        "content": [{"text": prompt}],
    })

    return messages


def _build_system(system_prompt: str) -> list[dict]:
    """Construir bloque de sistema para la API Converse.

    Args:
        system_prompt: Texto del prompt de sistema.

    Returns:
        Lista con el bloque de sistema, o lista vacía si no hay prompt.
    """
    if not system_prompt:
        return []
    return [{"text": system_prompt}]


def _extract_text(response: dict) -> str:
    """Extraer texto de la respuesta de la API Converse.

    Args:
        response: Respuesta completa de bedrock_client.converse().

    Returns:
        Texto extraído de la respuesta.

    Raises:
        RuntimeError: Si la respuesta tiene formato inesperado.
    """
    try:
        output = response.get("output", {})
        message = output.get("message", {})
        content_blocks = message.get("content", [])
        if content_blocks:
            return content_blocks[0].get("text", "")
        return ""
    except (KeyError, IndexError, TypeError, AttributeError) as exc:
        logger.error("Respuesta malformada de Bedrock: %s", exc)
        raise RuntimeError(DEFAULT_ERROR_MESSAGE) from exc


def _wait_backoff(attempt: int) -> None:
    """Esperar con backoff exponencial entre reintentos.

    Args:
        attempt: Número de intento actual (1-based).
    """
    wait_time = BASE_BACKOFF_SECONDS * (2 ** (attempt - 1))
    logger.info("Esperando %.1f segundos antes del reintento...", wait_time)
    time.sleep(wait_time)
