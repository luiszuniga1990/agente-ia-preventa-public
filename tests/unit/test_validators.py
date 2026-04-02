"""Tests unitarios para el módulo de validación."""

import json

import pytest

from src.utils.validators import (
    MAX_JSON_SIZE_BYTES,
    validate_email,
    validate_json_file,
    validate_partner_data,
    validate_service,
)


# --- validate_email ---


class TestValidateEmail:
    """Tests para validación de formato de correo electrónico."""

    @pytest.mark.parametrize(
        "email",
        [
            "user@example.com",
            "name@domain.co",
            "test.user@sub.domain.org",
            "a@b.c",
        ],
    )
    def test_valid_emails(self, email: str) -> None:
        assert validate_email(email) is True

    @pytest.mark.parametrize(
        "email",
        [
            "",
            "noatsign",
            "@domain.com",
            "user@",
            "user@domain",
            "user @example.com",
            "user@ example.com",
            "us er@example.com",
        ],
    )
    def test_invalid_emails(self, email: str) -> None:
        assert validate_email(email) is False

    def test_non_string_input(self) -> None:
        assert validate_email(None) is False  # type: ignore[arg-type]
        assert validate_email(123) is False  # type: ignore[arg-type]


# --- validate_partner_data ---


class TestValidatePartnerData:
    """Tests para validación de datos obligatorios del partner."""

    def test_all_fields_present(self) -> None:
        data = {
            "partner_name": "Acme Corp",
            "partner_email": "acme@example.com",
            "region": "LATAM",
            "end_customer": "Cliente Final",
        }
        is_valid, missing = validate_partner_data(data)
        assert is_valid is True
        assert missing == []

    def test_missing_single_field(self) -> None:
        data = {
            "partner_email": "acme@example.com",
            "region": "LATAM",
            "end_customer": "Cliente Final",
        }
        is_valid, missing = validate_partner_data(data)
        assert is_valid is False
        assert "partner_name" in missing

    def test_empty_string_field(self) -> None:
        data = {
            "partner_name": "",
            "partner_email": "acme@example.com",
            "region": "LATAM",
            "end_customer": "Cliente Final",
        }
        is_valid, missing = validate_partner_data(data)
        assert is_valid is False
        assert "partner_name" in missing

    def test_whitespace_only_field(self) -> None:
        data = {
            "partner_name": "   ",
            "partner_email": "acme@example.com",
            "region": "LATAM",
            "end_customer": "Cliente Final",
        }
        is_valid, missing = validate_partner_data(data)
        assert is_valid is False
        assert "partner_name" in missing

    def test_all_fields_missing(self) -> None:
        is_valid, missing = validate_partner_data({})
        assert is_valid is False
        assert len(missing) == 4

    def test_non_dict_input(self) -> None:
        is_valid, missing = validate_partner_data("not a dict")  # type: ignore[arg-type]
        assert is_valid is False
        assert len(missing) == 4


# --- validate_service ---


class TestValidateService:
    """Tests para validación de servicios soportados."""

    @pytest.mark.parametrize(
        "service",
        ["amazon_quick", "amazon_connect", "bedrock_agentcore"],
    )
    def test_supported_services(self, service: str) -> None:
        assert validate_service(service) is True

    @pytest.mark.parametrize(
        "service",
        ["amazon_s3", "lambda", "", "AMAZON_QUICK", "unknown"],
    )
    def test_unsupported_services(self, service: str) -> None:
        assert validate_service(service) is False


# --- validate_json_file ---


class TestValidateJsonFile:
    """Tests para validación de archivos JSON."""

    def test_valid_json(self) -> None:
        content = json.dumps({"key": "value"})
        is_valid, result = validate_json_file(content)
        assert is_valid is True
        assert result == {"key": "value"}

    def test_invalid_json(self) -> None:
        is_valid, result = validate_json_file("{invalid json}")
        assert is_valid is False
        assert isinstance(result, str)
        assert "JSON inválido" in result

    def test_empty_content(self) -> None:
        is_valid, result = validate_json_file("")
        assert is_valid is False
        assert "vacío" in result

    def test_exceeds_max_size(self) -> None:
        content = json.dumps({"data": "x" * (MAX_JSON_SIZE_BYTES + 1)})
        is_valid, result = validate_json_file(content)
        assert is_valid is False
        assert "1 MB" in result

    def test_non_string_input(self) -> None:
        is_valid, result = validate_json_file(123)  # type: ignore[arg-type]
        assert is_valid is False
        assert "cadena de texto" in result
