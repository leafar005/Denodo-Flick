"""
Tests unitarios para el cliente de Denodo AI SDK.
Valida la comunicación con los endpoints del AI SDK.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx

from app.denodo_client import (
    _strip_disclaimer,
    _parse_error,
    answer_metadata_question,
    answer_data_question,
    get_metadata,
    check_health,
    DENODO_AI_SDK_URL,
)


# ═══════════════════════════════════════════════════════════════
# Tests para _strip_disclaimer
# ═══════════════════════════════════════════════════════════════

class TestStripDisclaimer:
    def test_empty_string(self):
        assert _strip_disclaimer("") == ""

    def test_none_returns_none(self):
        assert _strip_disclaimer(None) is None

    def test_no_disclaimer(self):
        text = "Los 5 géneros más rentables son: Action, Comedy, Drama, Thriller, Horror."
        assert _strip_disclaimer(text) == text

    def test_strips_disclaimer_at_end(self):
        text = (
            "Los resultados muestran que Action es el género más rentable.\n\n"
            "**Disclaimer: Los datos provienen de TMDB y pueden no ser exactos."
        )
        result = _strip_disclaimer(text)
        assert "Disclaimer" not in result
        assert "Action" in result

    def test_strips_nota_at_end(self):
        text = (
            "El análisis indica una clara preferencia por el género Drama.\n\n"
            "**Nota: Esta información se basa en datos históricos."
        )
        result = _strip_disclaimer(text)
        assert "Nota:" not in result
        assert "Drama" in result

    def test_does_not_strip_disclaimer_in_first_half(self):
        text = "**Nota: importante. " + "X" * 200
        result = _strip_disclaimer(text)
        # Should not strip because it's in the first half
        assert "Nota:" in result

    def test_strips_please_note(self):
        long_content = "Datos importantes sobre películas. " * 10
        text = long_content + "\n\nPlease note that these results are approximate."
        result = _strip_disclaimer(text)
        assert "Please note" not in result


# ═══════════════════════════════════════════════════════════════
# Tests para _parse_error
# ═══════════════════════════════════════════════════════════════

class TestParseError:
    def test_json_with_detail_string(self):
        response = MagicMock()
        response.json.return_value = {"detail": "Not found"}
        assert _parse_error(response) == "Not found"

    def test_json_with_detail_dict(self):
        response = MagicMock()
        response.json.return_value = {"detail": {"error": "Database offline"}}
        assert _parse_error(response) == "Database offline"

    def test_plain_text_fallback(self):
        response = MagicMock()
        response.json.side_effect = Exception("Not JSON")
        response.text = "Internal Server Error"
        assert _parse_error(response) == "Internal Server Error"

    def test_status_code_fallback(self):
        response = MagicMock()
        response.json.side_effect = Exception("Not JSON")
        response.text = ""
        response.status_code = 503
        assert "503" in _parse_error(response)


# ═══════════════════════════════════════════════════════════════
# Tests para answer_metadata_question
# ═══════════════════════════════════════════════════════════════

class TestAnswerMetadataQuestion:
    @pytest.mark.asyncio
    @patch("app.denodo_client.httpx.AsyncClient")
    async def test_sends_correct_payload(self, mock_client_cls):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"answer": "Tabla movies encontrada"}

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await answer_metadata_question("¿Qué tablas hay?")

        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        payload = call_args[1]["json"]
        assert payload["question"] == "¿Qué tablas hay?"
        assert "custom_instructions" in payload
        assert result["answer"] == "Tabla movies encontrada"

    @pytest.mark.asyncio
    @patch("app.denodo_client.httpx.AsyncClient")
    async def test_sends_use_views_when_provided(self, mock_client_cls):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"answer": "OK"}

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        await answer_metadata_question("Test", use_views="admin.movies")

        payload = mock_client.post.call_args[1]["json"]
        assert payload["use_views"] == "admin.movies"

    @pytest.mark.asyncio
    @patch("app.denodo_client.httpx.AsyncClient")
    async def test_raises_on_error_status(self, mock_client_cls):
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.json.return_value = {"detail": "Internal error"}

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        with pytest.raises(Exception, match="Internal error"):
            await answer_metadata_question("Test")


# ═══════════════════════════════════════════════════════════════
# Tests para answer_data_question
# ═══════════════════════════════════════════════════════════════

class TestAnswerDataQuestion:
    @pytest.mark.asyncio
    @patch("app.denodo_client.httpx.AsyncClient")
    async def test_sends_correct_payload(self, mock_client_cls):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"answer": "Top 5 movies: ..."}

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await answer_data_question("Top 5 películas")

        payload = mock_client.post.call_args[1]["json"]
        assert payload["question"] == "Top 5 películas"
        assert result["answer"] == "Top 5 movies: ..."


# ═══════════════════════════════════════════════════════════════
# Tests para check_health
# ═══════════════════════════════════════════════════════════════

class TestCheckHealth:
    @pytest.mark.asyncio
    @patch("app.denodo_client.httpx.AsyncClient")
    async def test_connected(self, mock_client_cls):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "healthy"}

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await check_health()
        assert result["status"] is True
        assert result["data"] is not None

    @pytest.mark.asyncio
    @patch("app.denodo_client.httpx.AsyncClient")
    async def test_disconnected(self, mock_client_cls):
        mock_client = AsyncMock()
        mock_client.get.side_effect = Exception("Connection refused")
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await check_health()
        assert result["status"] is False
