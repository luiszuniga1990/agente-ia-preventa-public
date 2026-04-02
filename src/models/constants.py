"""Constantes globales del sistema Agente IA Preventa."""

# Servicios soportados para generación de estimaciones
SUPPORTED_SERVICES: list[str] = [
    "amazon_quick",
    "amazon_connect",
    "bedrock_agentcore",
]

# Idiomas soportados (códigos ISO 639-1)
SUPPORTED_LANGUAGES: list[str] = ["es", "en", "pt", "de"]

# Estados válidos de una conversación
CONVERSATION_STATUSES: list[str] = ["active", "completed"]

# Moneda por defecto para estimaciones
DEFAULT_CURRENCY: str = "USD"
