"""Tests unitarios para el detector de idioma."""

import pytest

from src.utils.language_detector import (
    DEFAULT_LANGUAGE,
    UNSUPPORTED_LANGUAGE_MESSAGE,
    detect_language,
    get_unsupported_language_message,
    is_supported_language,
)


class TestDetectLanguage:
    """Tests para la función detect_language."""

    def test_detecta_español(self):
        """Detecta español con palabras clave comunes."""
        assert detect_language("Hola, quiero una estimación de costos") == "es"

    def test_detecta_ingles(self):
        """Detecta inglés con palabras clave comunes."""
        assert detect_language("Hello, I need a cost estimation please") == "en"

    def test_detecta_portugues(self):
        """Detecta portugués con palabras clave comunes."""
        assert detect_language("Olá, preciso de uma estimativa de custos") == "pt"

    def test_detecta_aleman(self):
        """Detecta alemán con palabras clave comunes."""
        assert detect_language("Hallo, ich brauche eine Kostenschätzung bitte") == "de"

    def test_texto_vacio_retorna_default(self):
        """Texto vacío retorna idioma por defecto (inglés)."""
        assert detect_language("") == DEFAULT_LANGUAGE

    def test_texto_solo_espacios_retorna_default(self):
        """Texto con solo espacios retorna idioma por defecto."""
        assert detect_language("   ") == DEFAULT_LANGUAGE

    def test_texto_sin_coincidencias_retorna_default(self):
        """Texto sin palabras clave reconocidas retorna idioma por defecto."""
        assert detect_language("xyz123 abc456") == DEFAULT_LANGUAGE

    def test_none_retorna_default(self):
        """Entrada None retorna idioma por defecto."""
        assert detect_language(None) == DEFAULT_LANGUAGE

    def test_no_string_retorna_default(self):
        """Entrada no string retorna idioma por defecto."""
        assert detect_language(123) == DEFAULT_LANGUAGE

    def test_español_con_servicio(self):
        """Detecta español en contexto de estimación de servicio."""
        assert detect_language("Necesito el precio del servicio para los usuarios") == "es"

    def test_ingles_con_servicio(self):
        """Detecta inglés en contexto de estimación de servicio."""
        assert detect_language("What is the monthly cost for this service") == "en"


class TestIsSupportedLanguage:
    """Tests para la función is_supported_language."""

    @pytest.mark.parametrize("lang", ["es", "en", "pt", "de"])
    def test_idiomas_soportados(self, lang):
        """Todos los idiomas soportados retornan True."""
        assert is_supported_language(lang) is True

    @pytest.mark.parametrize("lang", ["fr", "it", "ja", "zh", "ru", "", "ES", "EN"])
    def test_idiomas_no_soportados(self, lang):
        """Idiomas no soportados retornan False."""
        assert is_supported_language(lang) is False


class TestGetUnsupportedLanguageMessage:
    """Tests para la función get_unsupported_language_message."""

    def test_retorna_mensaje_en_ingles(self):
        """El mensaje de idioma no soportado está en inglés."""
        msg = get_unsupported_language_message()
        assert msg == UNSUPPORTED_LANGUAGE_MESSAGE

    def test_mensaje_lista_idiomas(self):
        """El mensaje lista los 4 idiomas disponibles."""
        msg = get_unsupported_language_message()
        assert "Spanish" in msg
        assert "English" in msg
        assert "Portuguese" in msg
        assert "German" in msg

    def test_mensaje_lista_codigos(self):
        """El mensaje incluye los códigos ISO de los idiomas."""
        msg = get_unsupported_language_message()
        assert "(es)" in msg
        assert "(en)" in msg
        assert "(pt)" in msg
        assert "(de)" in msg
