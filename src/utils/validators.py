"""Módulo de validación para datos de entrada del sistema Agente IA Preventa."""

import json
import re

from src.models.constants import SUPPORTED_SERVICES

# Tamaño máximo permitido para archivos JSON (1 MB)
MAX_JSON_SIZE_BYTES: int = 1_048_576

# Campos obligatorios para datos del partner
REQUIRED_PARTNER_FIELDS: list[str] = [
    "partner_name",
    "partner_email",
    "region",
    "end_customer",
]

# Regex simple para validación de email
_EMAIL_REGEX = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def validate_email(email: str) -> bool:
    """Valida que una cadena tenga formato estándar de correo electrónico.

    Verifica que el email contenga exactamente un '@', que el dominio
    tenga al menos un '.', y que no contenga espacios.

    Args:
        email: Cadena a validar como correo electrónico.

    Returns:
        True si el formato es válido, False en caso contrario.
    """
    if not isinstance(email, str) or not email:
        return False
    return bool(_EMAIL_REGEX.match(email))


def validate_partner_data(data: dict) -> tuple[bool, list[str]]:
    """Verifica que los datos del partner contengan todos los campos obligatorios.

    Los campos obligatorios son: partner_name, partner_email, region y end_customer.
    Cada campo debe existir y ser una cadena no vacía.

    Args:
        data: Diccionario con los datos del partner.

    Returns:
        Tupla (es_válido, campos_faltantes) donde es_válido es True si todos
        los campos están presentes y no vacíos, y campos_faltantes es la lista
        de campos que faltan o están vacíos.
    """
    if not isinstance(data, dict):
        return False, list(REQUIRED_PARTNER_FIELDS)

    missing_fields: list[str] = []
    for field in REQUIRED_PARTNER_FIELDS:
        value = data.get(field)
        if not isinstance(value, str) or not value.strip():
            missing_fields.append(field)

    is_valid = len(missing_fields) == 0
    return is_valid, missing_fields


def validate_service(service: str) -> bool:
    """Verifica que el servicio solicitado esté en la lista de servicios soportados.

    Args:
        service: Nombre del servicio a validar.

    Returns:
        True si el servicio está soportado, False en caso contrario.
    """
    return service in SUPPORTED_SERVICES


def validate_json_file(content: str) -> tuple[bool, dict | str]:
    """Parsea y valida una cadena como JSON, verificando que no supere 1 MB.

    Args:
        content: Cadena con el contenido JSON a validar.

    Returns:
        Tupla (es_válido, resultado) donde resultado es el dict parseado
        si es válido, o un mensaje de error descriptivo si no lo es.
    """
    if not isinstance(content, str):
        return False, "El contenido debe ser una cadena de texto"

    if not content.strip():
        return False, "El contenido está vacío"

    size_bytes = len(content.encode("utf-8"))
    if size_bytes > MAX_JSON_SIZE_BYTES:
        return (
            False,
            f"El archivo excede el tamaño máximo permitido de 1 MB "
            f"({size_bytes:,} bytes)",
        )

    try:
        data = json.loads(content)
    except json.JSONDecodeError as e:
        return False, f"JSON inválido: {e}"

    return True, data
