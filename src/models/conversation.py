"""Modelo de datos para conversaciones."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
import uuid


@dataclass
class Conversation:
    """Representa una conversación entre un usuario y el agente.

    Atributos:
        conversation_id: Identificador único (UUID) de la conversación.
        user_id: ID del usuario (Cognito sub).
        messages: Lista de mensajes [{role, content, timestamp}].
        language: Idioma detectado de la conversación (es/en/pt/de).
        status: Estado de la conversación (active/completed).
        created_at: Fecha de creación en formato ISO8601.
        updated_at: Fecha de última actualización en formato ISO8601.
    """

    conversation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = ""
    messages: list[dict[str, Any]] = field(default_factory=list)
    language: str = "es"
    status: str = "active"
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    updated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
