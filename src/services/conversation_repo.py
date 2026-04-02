"""Repositorio de conversaciones en DynamoDB.

Gestiona operaciones CRUD sobre la tabla `conversations`.
Esquema: PK=conversation_id, SK=user_id, GSI user_id-index (PK=user_id, SK=created_at).
"""

from datetime import datetime, timezone

from src.models import Conversation


def create_conversation(dynamodb, user_id: str, language: str) -> Conversation:
    """Crear nueva conversación con UUID y guardarla en DynamoDB.

    Args:
        dynamodb: Recurso boto3 de DynamoDB.
        user_id: ID del usuario (Cognito sub).
        language: Idioma detectado (es/en/pt/de).

    Returns:
        Objeto Conversation creado.
    """
    conversation = Conversation(user_id=user_id, language=language)
    table = dynamodb.Table("conversations")
    table.put_item(
        Item={
            "conversation_id": conversation.conversation_id,
            "user_id": conversation.user_id,
            "language": conversation.language,
            "messages": conversation.messages,
            "status": conversation.status,
            "created_at": conversation.created_at,
            "updated_at": conversation.updated_at,
        }
    )
    return conversation


def get_conversation(dynamodb, conversation_id: str) -> Conversation | None:
    """Obtener conversación por conversation_id usando query en la PK.

    Como la tabla tiene clave compuesta (conversation_id + user_id),
    se usa query sobre la PK para obtener la conversación sin necesitar user_id.

    Args:
        dynamodb: Recurso boto3 de DynamoDB.
        conversation_id: ID único de la conversación.

    Returns:
        Objeto Conversation o None si no existe.
    """
    table = dynamodb.Table("conversations")
    response = table.query(
        KeyConditionExpression="conversation_id = :cid",
        ExpressionAttributeValues={":cid": conversation_id},
        Limit=1,
    )
    items = response.get("Items", [])
    if not items:
        return None
    item = items[0]
    return _item_to_conversation(item)


def add_message(
    dynamodb, conversation_id: str, user_id: str, role: str, content: str
) -> None:
    """Agregar mensaje a la lista de mensajes de una conversación.

    Usa UpdateExpression con list_append para agregar mensajes atómicamente.

    Args:
        dynamodb: Recurso boto3 de DynamoDB.
        conversation_id: ID de la conversación.
        user_id: ID del usuario (necesario como SK).
        role: Rol del mensaje (user/assistant).
        content: Contenido del mensaje.
    """
    table = dynamodb.Table("conversations")
    now = datetime.now(timezone.utc).isoformat()
    message = {"role": role, "content": content, "timestamp": now}
    table.update_item(
        Key={"conversation_id": conversation_id, "user_id": user_id},
        UpdateExpression="SET messages = list_append(if_not_exists(messages, :empty), :msg), updated_at = :now",
        ExpressionAttributeValues={
            ":msg": [message],
            ":empty": [],
            ":now": now,
        },
    )


def list_conversations(dynamodb, user_id: str) -> list[Conversation]:
    """Listar conversaciones del usuario ordenadas por fecha descendente.

    Usa el GSI user_id-index para consultar por user_id.

    Args:
        dynamodb: Recurso boto3 de DynamoDB.
        user_id: ID del usuario.

    Returns:
        Lista de conversaciones ordenadas por fecha descendente.
    """
    table = dynamodb.Table("conversations")
    response = table.query(
        IndexName="user_id-index",
        KeyConditionExpression="user_id = :uid",
        ExpressionAttributeValues={":uid": user_id},
        ScanIndexForward=False,
    )
    items = response.get("Items", [])
    return [_item_to_conversation(item) for item in items]


def update_status(
    dynamodb, conversation_id: str, user_id: str, status: str
) -> None:
    """Actualizar estado de una conversación (active/completed).

    Args:
        dynamodb: Recurso boto3 de DynamoDB.
        conversation_id: ID de la conversación.
        user_id: ID del usuario (necesario como SK).
        status: Nuevo estado (active/completed).
    """
    table = dynamodb.Table("conversations")
    now = datetime.now(timezone.utc).isoformat()
    table.update_item(
        Key={"conversation_id": conversation_id, "user_id": user_id},
        UpdateExpression="SET #s = :status, updated_at = :now",
        ExpressionAttributeNames={"#s": "status"},
        ExpressionAttributeValues={":status": status, ":now": now},
    )


def _item_to_conversation(item: dict) -> Conversation:
    """Convertir un item de DynamoDB a un objeto Conversation.

    Args:
        item: Diccionario con los datos del item.

    Returns:
        Objeto Conversation.
    """
    return Conversation(
        conversation_id=item.get("conversation_id", ""),
        user_id=item.get("user_id", ""),
        messages=item.get("messages", []),
        language=item.get("language", "es"),
        status=item.get("status", "active"),
        created_at=item.get("created_at", ""),
        updated_at=item.get("updated_at", ""),
    )
