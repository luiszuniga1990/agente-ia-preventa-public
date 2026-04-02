"""Scraper de precios desde URLs oficiales de AWS.

Obtiene y parsea datos de precios de Amazon Quick, Amazon Connect
y Bedrock AgentCore desde sus páginas oficiales de pricing.
"""

import logging
import re
from typing import Callable

import requests

logger = logging.getLogger(__name__)

# Timeout para peticiones HTTP (segundos)
HTTP_TIMEOUT = 30

# URLs oficiales de pricing por servicio
PRICING_URLS: dict[str, str] = {
    "amazon_quick": "https://aws.amazon.com/quick/pricing/",
    "amazon_connect": "https://aws.amazon.com/es/connect/pricing/",
    "bedrock_agentcore": "https://aws.amazon.com/bedrock/agentcore/pricing/",
}


def fetch_pricing(service_id: str, url: str) -> list[dict]:
    """Obtener datos de precios desde una URL oficial de AWS.

    Hace HTTP GET a la URL, parsea el HTML y extrae datos de precios
    estructurados.

    Args:
        service_id: Identificador del servicio (amazon_quick, amazon_connect,
            bedrock_agentcore).
        url: URL oficial de pricing del servicio.

    Returns:
        Lista de dicts con claves: unit_price, unit, tier, currency,
        source_url, raw_data.

    Raises:
        ConnectionError: Si hay error de red o timeout.
        ValueError: Si el parsing del HTML falla.
    """
    html = _fetch_html(url)
    parser = _get_parser(service_id)
    return parser(html, url)


def _fetch_html(url: str) -> str:
    """Hacer HTTP GET a una URL y retornar el contenido HTML.

    Args:
        url: URL a consultar.

    Returns:
        Contenido HTML como string.

    Raises:
        ConnectionError: Si hay error de red, timeout o HTTP error.
    """
    try:
        response = requests.get(url, timeout=HTTP_TIMEOUT, headers={
            "User-Agent": "AWS-Pricing-Updater/1.0",
            "Accept": "text/html",
        })
        response.raise_for_status()
        return response.text
    except requests.exceptions.Timeout as exc:
        logger.error("Timeout al acceder a %s: %s", url, exc)
        raise ConnectionError(f"Timeout al acceder a {url}") from exc
    except requests.exceptions.HTTPError as exc:
        logger.error("Error HTTP al acceder a %s: %s", url, exc)
        raise ConnectionError(f"Error HTTP al acceder a {url}: {exc}") from exc
    except requests.exceptions.RequestException as exc:
        logger.error("Error de red al acceder a %s: %s", url, exc)
        raise ConnectionError(f"Error de red al acceder a {url}: {exc}") from exc


def _get_parser(service_id: str) -> Callable[[str, str], list[dict]]:
    """Obtener el parser específico para un servicio.

    Args:
        service_id: Identificador del servicio.

    Returns:
        Función parser para el servicio.

    Raises:
        ValueError: Si el servicio no tiene parser definido.
    """
    parsers: dict[str, Callable[[str, str], list[dict]]] = {
        "amazon_quick": _parse_quick_pricing,
        "amazon_connect": _parse_connect_pricing,
        "bedrock_agentcore": _parse_agentcore_pricing,
    }
    parser = parsers.get(service_id)
    if parser is None:
        raise ValueError(f"No hay parser definido para el servicio: {service_id}")
    return parser


def _parse_quick_pricing(html: str, source_url: str) -> list[dict]:
    """Parsear datos de precios de Amazon Quick.

    Extrae precios por usuario/mes y por funcionalidad desde el HTML.

    Args:
        html: Contenido HTML de la página de pricing.
        source_url: URL de origen para referencia.

    Returns:
        Lista de dicts con datos de precios.

    Raises:
        ValueError: Si el parsing falla.
    """
    try:
        return _extract_pricing_from_html(
            html, source_url, service_id="amazon_quick"
        )
    except Exception as exc:
        logger.error("Error parseando precios de Amazon Quick: %s", exc)
        raise ValueError(f"Error parseando precios de Amazon Quick: {exc}") from exc


def _parse_connect_pricing(html: str, source_url: str) -> list[dict]:
    """Parsear datos de precios de Amazon Connect.

    Extrae precios por minuto de llamada, por agente, etc.

    Args:
        html: Contenido HTML de la página de pricing.
        source_url: URL de origen para referencia.

    Returns:
        Lista de dicts con datos de precios.

    Raises:
        ValueError: Si el parsing falla.
    """
    try:
        return _extract_pricing_from_html(
            html, source_url, service_id="amazon_connect"
        )
    except Exception as exc:
        logger.error("Error parseando precios de Amazon Connect: %s", exc)
        raise ValueError(f"Error parseando precios de Amazon Connect: {exc}") from exc


def _parse_agentcore_pricing(html: str, source_url: str) -> list[dict]:
    """Parsear datos de precios de Bedrock AgentCore.

    Extrae precios por invocación, por componente, etc.

    Args:
        html: Contenido HTML de la página de pricing.
        source_url: URL de origen para referencia.

    Returns:
        Lista de dicts con datos de precios.

    Raises:
        ValueError: Si el parsing falla.
    """
    try:
        return _extract_pricing_from_html(
            html, source_url, service_id="bedrock_agentcore"
        )
    except Exception as exc:
        logger.error("Error parseando precios de Bedrock AgentCore: %s", exc)
        raise ValueError(
            f"Error parseando precios de Bedrock AgentCore: {exc}"
        ) from exc


def _extract_pricing_from_html(
    html: str, source_url: str, service_id: str
) -> list[dict]:
    """Extraer datos de precios genéricos desde HTML de AWS.

    Busca patrones de precios en el HTML (valores con $, tablas de precios)
    y los estructura en una lista de dicts.

    Args:
        html: Contenido HTML de la página.
        source_url: URL de origen.
        service_id: Identificador del servicio.

    Returns:
        Lista de dicts con datos de precios extraídos.
    """
    results: list[dict] = []

    # Patrón para encontrar precios: $X.XX por unidad
    price_pattern = re.compile(
        r"\$\s*([\d,]+\.?\d*)\s*(?:per|por|/)\s*([\w\s/]+)",
        re.IGNORECASE,
    )

    matches = price_pattern.findall(html)
    seen: set[tuple[str, str]] = set()

    for price_str, unit in matches:
        price_str_clean = price_str.replace(",", "")
        unit_clean = unit.strip().lower()[:50]
        key = (price_str_clean, unit_clean)
        if key in seen:
            continue
        seen.add(key)

        try:
            unit_price = float(price_str_clean)
        except ValueError:
            continue

        results.append({
            "unit_price": unit_price,
            "unit": unit_clean,
            "tier": "standard",
            "currency": "USD",
            "source_url": source_url,
            "raw_data": {
                "service_id": service_id,
                "matched_text": f"${price_str} per {unit}",
            },
        })

    # Si no se encontraron precios con el patrón principal, intentar
    # extraer de tablas HTML simples
    if not results:
        results = _extract_from_tables(html, source_url, service_id)

    return results


def _extract_from_tables(
    html: str, source_url: str, service_id: str
) -> list[dict]:
    """Extraer precios de tablas HTML como fallback.

    Busca celdas de tabla que contengan valores monetarios.

    Args:
        html: Contenido HTML.
        source_url: URL de origen.
        service_id: Identificador del servicio.

    Returns:
        Lista de dicts con datos de precios.
    """
    results: list[dict] = []

    # Buscar valores monetarios en celdas de tabla
    cell_pattern = re.compile(
        r"<td[^>]*>\s*\$\s*([\d,]+\.?\d*)\s*</td>",
        re.IGNORECASE,
    )

    for match in cell_pattern.finditer(html):
        price_str = match.group(1).replace(",", "")
        try:
            unit_price = float(price_str)
        except ValueError:
            continue

        results.append({
            "unit_price": unit_price,
            "unit": "unspecified",
            "tier": "standard",
            "currency": "USD",
            "source_url": source_url,
            "raw_data": {
                "service_id": service_id,
                "matched_text": match.group(0),
            },
        })

    return results
