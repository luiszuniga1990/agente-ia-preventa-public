"""Tests unitarios para el sistema de construcción de prompts."""

import pytest

from src.models.pricing import PricingEntry
from src.services.prompt_builder import (
    GUARDRAIL_MESSAGES,
    build_estimation_prompt,
    build_system_prompt,
)


def _sample_pricing() -> list[PricingEntry]:
    """Genera datos de pricing de ejemplo para tests."""
    return [
        PricingEntry(
            service_id="amazon_quick",
            component="User License",
            unit_price=25.00,
            unit="user/month",
            last_updated="2024-01-15T00:00:00Z",
        ),
        PricingEntry(
            service_id="amazon_connect",
            component="Voice Usage",
            unit_price=0.018,
            unit="minute",
            last_updated="2024-01-15T00:00:00Z",
        ),
    ]


class TestBuildSystemPrompt:
    """Tests para build_system_prompt."""

    def test_contiene_rol_del_agente(self):
        """El prompt incluye la definición del rol del agente."""
        prompt = build_system_prompt("en", [])
        assert "pre-sales cost estimation assistant" in prompt

    def test_contiene_servicios_soportados(self):
        """El prompt lista los 3 servicios soportados."""
        prompt = build_system_prompt("en", [])
        assert "Amazon Quick" in prompt
        assert "Amazon Connect" in prompt
        assert "Amazon Bedrock AgentCore" in prompt

    def test_contiene_guardrail(self):
        """El prompt incluye instrucciones de guardrail."""
        prompt = build_system_prompt("en", [])
        assert "Scope Guardrail" in prompt
        assert "in scope" in prompt
        assert "out of scope" in prompt

    def test_contiene_instruccion_clasificar_mensajes(self):
        """El prompt instruye clasificar cada mensaje antes de responder."""
        prompt = build_system_prompt("en", [])
        assert "classify EVERY user message" in prompt

    def test_contiene_instruccion_bloqueo(self):
        """El prompt instruye responder SOLO con mensaje de bloqueo si fuera de alcance."""
        prompt = build_system_prompt("en", [])
        assert "respond ONLY with the blocking message" in prompt

    def test_contiene_rechazo_override(self):
        """El prompt instruye rechazar intentos de override del prompt."""
        prompt = build_system_prompt("en", [])
        assert "REJECT" in prompt
        assert "override" in prompt

    @pytest.mark.parametrize("lang", ["es", "en", "pt", "de"])
    def test_contiene_mensaje_bloqueo_idioma(self, lang):
        """El prompt incluye el mensaje de bloqueo en el idioma solicitado."""
        prompt = build_system_prompt(lang, [])
        assert GUARDRAIL_MESSAGES[lang] in prompt

    def test_contiene_todos_mensajes_bloqueo(self):
        """El prompt incluye mensajes de bloqueo en los 4 idiomas."""
        prompt = build_system_prompt("en", [])
        for lang, msg in GUARDRAIL_MESSAGES.items():
            assert msg in prompt

    def test_contiene_instrucciones_idioma(self):
        """El prompt incluye instrucciones de idioma."""
        prompt = build_system_prompt("es", [])
        assert "Spanish" in prompt

    def test_contiene_few_shot_examples(self):
        """El prompt incluye few-shot examples."""
        prompt = build_system_prompt("en", [])
        assert "Few-Shot Examples" in prompt
        assert "Example 1" in prompt
        assert "Out of Scope Request" in prompt

    def test_contiene_datos_pricing(self):
        """El prompt incluye datos de pricing cuando se proporcionan."""
        pricing = _sample_pricing()
        prompt = build_system_prompt("en", pricing)
        assert "User License" in prompt
        assert "$25.0000" in prompt
        assert "user/month" in prompt

    def test_sin_pricing_muestra_mensaje(self):
        """Sin datos de pricing muestra mensaje apropiado."""
        prompt = build_system_prompt("en", [])
        assert "No pricing data available" in prompt

    def test_contiene_formato_respuesta(self):
        """El prompt incluye formato de respuesta para estimaciones."""
        prompt = build_system_prompt("en", [])
        assert "Cost breakdown" in prompt
        assert "Monthly total" in prompt
        assert "Annual total" in prompt

    def test_contiene_recoleccion_datos_partner(self):
        """El prompt incluye instrucciones de recolección de datos del partner."""
        prompt = build_system_prompt("en", [])
        assert "Partner" in prompt
        assert "email" in prompt.lower()

    def test_idioma_no_soportado_usa_ingles(self):
        """Un idioma no soportado usa inglés como fallback."""
        prompt = build_system_prompt("fr", [])
        assert "English" in prompt
        assert GUARDRAIL_MESSAGES["en"] in prompt


class TestBuildEstimationPrompt:
    """Tests para build_estimation_prompt."""

    def test_contiene_nombre_servicio(self):
        """El prompt incluye el nombre del servicio."""
        prompt = build_estimation_prompt(
            "amazon_quick", {"num_users": 50}, _sample_pricing(), "en"
        )
        assert "Amazon Quick" in prompt

    def test_contiene_parametros(self):
        """El prompt incluye los parámetros proporcionados."""
        params = {"num_users": 50, "expected_volume": "medium"}
        prompt = build_estimation_prompt("amazon_quick", params, [], "en")
        assert "num_users: 50" in prompt
        assert "expected_volume: medium" in prompt

    def test_contiene_parametros_anidados(self):
        """El prompt formatea correctamente parámetros anidados (dict)."""
        params = {
            "concurrent_agents": 20,
            "additional_features": {"recording": True, "chat": False},
        }
        prompt = build_estimation_prompt("amazon_connect", params, [], "en")
        assert "recording: True" in prompt
        assert "chat: False" in prompt

    def test_contiene_datos_pricing(self):
        """El prompt incluye datos de pricing para el cálculo."""
        pricing = _sample_pricing()
        prompt = build_estimation_prompt("amazon_quick", {}, pricing, "en")
        assert "Pricing Data" in prompt
        assert "User License" in prompt

    def test_contiene_formato_salida_requerido(self):
        """El prompt especifica el formato de salida requerido."""
        prompt = build_estimation_prompt("amazon_quick", {}, [], "en")
        assert "Cost breakdown table" in prompt
        assert "monthly cost" in prompt.lower()
        assert "annual cost" in prompt.lower()
        assert "assumptions" in prompt.lower()

    def test_contiene_disclaimer(self):
        """El prompt solicita incluir disclaimer de costos aproximados."""
        prompt = build_estimation_prompt("amazon_quick", {}, [], "en")
        assert "approximate" in prompt.lower()
        assert "subject to change" in prompt.lower()

    def test_idioma_español(self):
        """El prompt solicita respuesta en español."""
        prompt = build_estimation_prompt("amazon_quick", {}, [], "es")
        assert "Spanish" in prompt

    def test_idioma_aleman(self):
        """El prompt solicita respuesta en alemán."""
        prompt = build_estimation_prompt("amazon_quick", {}, [], "de")
        assert "German" in prompt

    def test_sin_parametros(self):
        """El prompt maneja correctamente la ausencia de parámetros."""
        prompt = build_estimation_prompt("amazon_quick", {}, [], "en")
        assert "No parameters provided" in prompt


class TestGuardrailMessages:
    """Tests para los mensajes de guardrail."""

    def test_cuatro_idiomas_definidos(self):
        """Hay mensajes de bloqueo para los 4 idiomas soportados."""
        assert len(GUARDRAIL_MESSAGES) == 4
        assert set(GUARDRAIL_MESSAGES.keys()) == {"es", "en", "pt", "de"}

    def test_mensaje_español(self):
        """El mensaje en español es correcto."""
        assert "Solo puedo asistirte" in GUARDRAIL_MESSAGES["es"]
        assert "Amazon Quick" in GUARDRAIL_MESSAGES["es"]

    def test_mensaje_ingles(self):
        """El mensaje en inglés es correcto."""
        assert "I can only assist" in GUARDRAIL_MESSAGES["en"]
        assert "Amazon Quick" in GUARDRAIL_MESSAGES["en"]

    def test_mensaje_portugues(self):
        """El mensaje en portugués es correcto."""
        assert "Só posso ajudá-lo" in GUARDRAIL_MESSAGES["pt"]
        assert "Amazon Quick" in GUARDRAIL_MESSAGES["pt"]

    def test_mensaje_aleman(self):
        """El mensaje en alemán es correcto."""
        assert "Ich kann Ihnen nur" in GUARDRAIL_MESSAGES["de"]
        assert "Amazon Quick" in GUARDRAIL_MESSAGES["de"]

    @pytest.mark.parametrize("lang", ["es", "en", "pt", "de"])
    def test_mensajes_mencionan_tres_servicios(self, lang):
        """Cada mensaje menciona los 3 servicios soportados."""
        msg = GUARDRAIL_MESSAGES[lang]
        assert "Amazon Quick" in msg
        assert "Amazon Connect" in msg
        assert "Amazon Bedrock AgentCore" in msg
