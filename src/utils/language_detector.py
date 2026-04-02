"""Detector de idioma basado en palabras clave para el Agente IA Preventa.

Detecta el idioma del texto del usuario entre los 4 idiomas soportados
(es, en, pt, de) usando un enfoque simple de palabras clave comunes.
No requiere dependencias pesadas de NLP.
"""

from src.models.constants import SUPPORTED_LANGUAGES

# Idioma por defecto cuando no se puede determinar
DEFAULT_LANGUAGE: str = "en"

# Mensaje de idioma no soportado (en inglés por defecto)
UNSUPPORTED_LANGUAGE_MESSAGE: str = (
    "The detected language is not supported. "
    "Supported languages are: Spanish (es), English (en), "
    "Portuguese (pt), and German (de)."
)

# Palabras clave comunes por idioma para detección simple.
# Se priorizan palabras funcionales (artículos, preposiciones, pronombres)
# que son frecuentes y distintivas de cada idioma.
_LANGUAGE_KEYWORDS: dict[str, set[str]] = {
    "es": {
        "el", "la", "los", "las", "de", "del", "en", "un", "una", "que",
        "por", "para", "con", "como", "pero", "más", "este", "esta",
        "estos", "estas", "ser", "hola", "quiero", "necesito", "puedo",
        "cuánto", "cuanto", "cuesta", "precio", "estimación", "estimacion",
        "servicio", "servicios", "ayuda", "gracias", "también", "tambien",
        "sobre", "tiene", "puede", "hacer", "tengo", "estoy", "somos",
        "nuestro", "nuestra", "cliente", "costo", "costos", "mensual",
        "anual", "usuario", "usuarios",
    },
    "en": {
        "the", "is", "are", "was", "were", "have", "has", "had", "do",
        "does", "did", "will", "would", "could", "should", "can", "may",
        "might", "shall", "must", "need", "want", "hello", "hi", "please",
        "thank", "thanks", "how", "much", "many", "what", "which", "where",
        "when", "who", "why", "this", "that", "these", "those", "with",
        "from", "about", "into", "through", "during", "before", "after",
        "between", "estimate", "estimation", "cost", "price", "service",
        "monthly", "annual", "user", "users",
    },
    "pt": {
        "o", "os", "um", "uma", "uns", "umas", "do", "da", "dos", "das",
        "no", "na", "nos", "nas", "ao", "aos", "pelo", "pela", "com",
        "como", "para", "por", "mas", "mais", "este", "esta", "esse",
        "essa", "aquele", "aquela", "ser", "ter", "olá", "ola", "quero",
        "preciso", "posso", "quanto", "custa", "preço", "preco",
        "estimativa", "serviço", "servico", "ajuda", "obrigado",
        "obrigada", "também", "tambem", "sobre", "tem", "pode", "fazer",
        "tenho", "estou", "somos", "nosso", "nossa", "cliente", "custo",
        "custos", "mensal", "anual", "usuário", "usuario", "usuários",
    },
    "de": {
        "der", "die", "das", "den", "dem", "des", "ein", "eine", "einen",
        "einem", "einer", "und", "ist", "sind", "war", "hat", "haben",
        "wird", "kann", "können", "konnen", "soll", "muss", "ich", "du",
        "er", "sie", "wir", "ihr", "hallo", "bitte", "danke", "wie",
        "viel", "was", "welche", "welcher", "wo", "wann", "wer", "warum",
        "mit", "von", "über", "uber", "für", "fur", "nach", "vor",
        "zwischen", "schätzung", "schatzung", "kosten", "preis", "dienst",
        "monatlich", "jährlich", "jahrlich", "benutzer",
    },
}


def detect_language(text: str) -> str:
    """Detecta el idioma del texto entre los 4 idiomas soportados.

    Usa un enfoque de conteo de palabras clave comunes en cada idioma.
    Si no se puede determinar el idioma, retorna el idioma por defecto (inglés).

    Args:
        text: Texto del usuario a analizar.

    Returns:
        Código ISO 639-1 del idioma detectado (es, en, pt, de).
    """
    if not isinstance(text, str) or not text.strip():
        return DEFAULT_LANGUAGE

    # Normalizar: minúsculas y extraer palabras
    words = set(text.lower().split())

    # Contar coincidencias con palabras clave de cada idioma
    scores: dict[str, int] = {}
    for lang, keywords in _LANGUAGE_KEYWORDS.items():
        scores[lang] = len(words & keywords)

    max_score = max(scores.values())

    # Si no hay coincidencias, retornar idioma por defecto
    if max_score == 0:
        return DEFAULT_LANGUAGE

    # Retornar el idioma con mayor puntuación
    detected = max(scores, key=lambda lang: scores[lang])
    return detected


def is_supported_language(lang_code: str) -> bool:
    """Verifica si un código de idioma está entre los idiomas soportados.

    Args:
        lang_code: Código ISO 639-1 del idioma a verificar.

    Returns:
        True si el idioma está soportado, False en caso contrario.
    """
    return lang_code in SUPPORTED_LANGUAGES


def get_unsupported_language_message() -> str:
    """Retorna el mensaje de idioma no soportado en inglés.

    El mensaje lista los 4 idiomas disponibles para que el usuario
    pueda reformular su consulta en uno de ellos.

    Returns:
        Mensaje indicando los idiomas soportados.
    """
    return UNSUPPORTED_LANGUAGE_MESSAGE
