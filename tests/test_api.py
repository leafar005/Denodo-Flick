"""
Tests de integración para la API FastAPI (main.py).
Verifica los endpoints REST de DecisionLens.
"""

import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient, ASGITransport

from app.main import app


@pytest.fixture
def transport():
    return ASGITransport(app=app)


# ═══════════════════════════════════════════════════════════════
# Tests para endpoints GET
# ═══════════════════════════════════════════════════════════════

class TestGetEndpoints:
    @pytest.mark.asyncio
    async def test_home_returns_html(self, transport):
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            res = await client.get("/")
            assert res.status_code == 200
            assert "text/html" in res.headers["content-type"]
            assert "DecisionLens" in res.text

    @pytest.mark.asyncio
    @patch("app.main.check_health")
    async def test_health_connected(self, mock_health, transport):
        mock_health.return_value = {"status": True, "data": {"status": "healthy"}}
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            res = await client.get("/api/health")
            data = res.json()
            assert data["app"] == "ok"
            assert data["denodo_ai_sdk"] == "connected"

    @pytest.mark.asyncio
    @patch("app.main.check_health")
    async def test_health_disconnected(self, mock_health, transport):
        mock_health.return_value = {"status": False, "error": "Connection refused"}
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            res = await client.get("/api/health")
            data = res.json()
            assert data["denodo_ai_sdk"] == "disconnected"

    @pytest.mark.asyncio
    async def test_get_scenarios(self, transport):
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            res = await client.get("/api/scenarios")
            data = res.json()
            assert "production" in data
            assert "investment" in data
            assert "distribution" in data
            assert "custom" in data

    @pytest.mark.asyncio
    async def test_get_scenario_detail(self, transport):
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            res = await client.get("/api/scenarios/production")
            data = res.json()
            assert data["key"] == "production"
            assert "metadata_questions" in data
            assert "data_questions" in data
            assert len(data["metadata_questions"]) > 0

    @pytest.mark.asyncio
    async def test_get_scenario_not_found(self, transport):
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            res = await client.get("/api/scenarios/nonexistent")
            data = res.json()
            assert "error" in data


# ═══════════════════════════════════════════════════════════════
# Tests para /api/decide
# ═══════════════════════════════════════════════════════════════

class TestDecideEndpoint:
    @pytest.mark.asyncio
    @patch("app.main.run_decision_pipeline")
    async def test_decide_calls_pipeline(self, mock_pipeline, transport):
        mock_pipeline.return_value = {
            "scenario": "Test",
            "phase1_metadata": [],
            "phase2_data": [],
            "decision": "Recomendación de test",
            "errors": [],
        }
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            res = await client.post("/api/decide", json={
                "scenario": "production",
            })
            data = res.json()
            assert data["decision"] == "Recomendación de test"
            mock_pipeline.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.main.run_decision_pipeline")
    async def test_decide_with_params(self, mock_pipeline, transport):
        mock_pipeline.return_value = {"decision": "OK", "errors": []}
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            await client.post("/api/decide", json={
                "scenario": "production",
                "parameters": {"genre": "Action"},
                "use_views": "admin.movies",
            })
            call_kwargs = mock_pipeline.call_args[1]
            assert call_kwargs["params"] == {"genre": "Action"}
            assert call_kwargs["use_views"] == "admin.movies"


# ═══════════════════════════════════════════════════════════════
# Tests para /api/discover-views
# ═══════════════════════════════════════════════════════════════

class TestDiscoverViews:
    @pytest.mark.asyncio
    @patch("app.main.answer_metadata_question")
    async def test_discover_views_ok(self, mock_meta, transport):
        mock_meta.return_value = {
            "answer": "Las vistas disponibles son: admin.movies, admin.movies_small, admin.genres"
        }
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            res = await client.get("/api/discover-views")
            data = res.json()
            assert data["status"] == "ok"
            assert "admin.movies" in data["answer"]

    @pytest.mark.asyncio
    @patch("app.main.answer_metadata_question")
    async def test_discover_views_error(self, mock_meta, transport):
        mock_meta.side_effect = Exception("SDK offline")
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            res = await client.get("/api/discover-views")
            data = res.json()
            assert data["status"] == "error"
            assert "SDK offline" in data["error"]


# ═══════════════════════════════════════════════════════════════
# Tests para /api/ask
# ═══════════════════════════════════════════════════════════════

class TestAskEndpoint:
    @pytest.mark.asyncio
    @patch("app.main.answer_data_question")
    async def test_ask_data_phase(self, mock_data, transport):
        mock_data.return_value = {"answer": "Respuesta de datos"}
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            res = await client.post("/api/ask", json={
                "question": "¿Cuántas películas hay?",
                "phase": "data",
            })
            data = res.json()
            assert data["answer"] == "Respuesta de datos"

    @pytest.mark.asyncio
    @patch("app.main.answer_metadata_question")
    async def test_ask_metadata_phase(self, mock_meta, transport):
        mock_meta.return_value = {"answer": "Tablas disponibles: movies"}
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            res = await client.post("/api/ask", json={
                "question": "¿Qué tablas hay?",
                "phase": "metadata",
            })
            data = res.json()
            assert data["answer"] == "Tablas disponibles: movies"

    @pytest.mark.asyncio
    @patch("app.main.answer_data_question")
    async def test_ask_handles_error(self, mock_data, transport):
        mock_data.side_effect = Exception("Connection failed")
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            res = await client.post("/api/ask", json={
                "question": "Test",
            })
            data = res.json()
            assert data["answer"] is None
            assert "Connection failed" in data["error"]
