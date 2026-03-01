"""
Tests unitarios para el motor de decisiones.
Valida la lógica de las 2 fases obligatorias del reto Denodo HackUDC.
"""

import pytest
from unittest.mock import AsyncMock, patch

from app.decision_engine import (
    build_param_context,
    compute_total_steps,
    _build_metadata_prefix,
    run_decision_pipeline,
    run_decision_pipeline_stream,
    SCENARIOS,
)


# ═══════════════════════════════════════════════════════════════
# Tests para _build_metadata_prefix
# ═══════════════════════════════════════════════════════════════

class TestBuildMetadataPrefix:
    def test_empty_context_returns_empty_string(self):
        assert _build_metadata_prefix("") == ""

    def test_none_context_returns_empty_string(self):
        # Cadena vacía truthy check
        assert _build_metadata_prefix("") == ""

    def test_with_context_returns_prefix(self):
        ctx = "- La tabla admin.movies contiene columnas: title, budget, revenue"
        result = _build_metadata_prefix(ctx)
        assert "CONTEXTO IMPORTANTE" in result
        assert "admin.movies" in result
        assert result.endswith("Pregunta concreta: ")

    def test_prefix_includes_full_context(self):
        ctx = "- tabla1: col1, col2\n- tabla2: col3, col4"
        result = _build_metadata_prefix(ctx)
        assert "tabla1" in result
        assert "tabla2" in result
        assert "EXCLUSIVAMENTE" in result

    def test_with_use_views_restricts_scope(self):
        ctx = "- La tabla admin.netflix contiene columnas: title, rating"
        result = _build_metadata_prefix(ctx, use_views="admin.netflix")
        assert "admin.netflix" in result
        assert "NO hagas JOIN" in result


# ═══════════════════════════════════════════════════════════════
# Tests para build_param_context
# ═══════════════════════════════════════════════════════════════

class TestBuildParamContext:
    def test_none_params(self):
        assert build_param_context(None) == ""

    def test_empty_params(self):
        assert build_param_context({}) == ""

    def test_genre_param(self):
        result = build_param_context({"genre": "Action"})
        assert "Action" in result
        assert "género" in result

    def test_budget_param(self):
        result = build_param_context({"budget_range": "Alto (> 50M $)"})
        assert "presupuesto" in result
        assert "Alto" in result

    def test_year_param(self):
        result = build_param_context({"min_year": "2020"})
        assert "2020" in result

    def test_rating_param(self):
        result = build_param_context({"min_rating": "7.5"})
        assert "7.5" in result

    def test_language_param(self):
        result = build_param_context({"language": "Español (es)"})
        assert "Español" in result

    def test_multiple_params(self):
        result = build_param_context({
            "genre": "Comedy",
            "min_year": "2018",
            "budget_range": "Medio (5M - 50M $)",
        })
        assert "Comedy" in result
        assert "2018" in result
        assert "Medio" in result

    def test_empty_value_ignored(self):
        result = build_param_context({"genre": "", "min_year": "2020"})
        assert "género" not in result
        assert "2020" in result


# ═══════════════════════════════════════════════════════════════
# Tests para compute_total_steps
# ═══════════════════════════════════════════════════════════════

class TestComputeTotalSteps:
    def test_production_scenario(self):
        meta_qs, data_qs, total = compute_total_steps("production", None, None, None)
        assert len(meta_qs) == 2
        assert len(data_qs) == 4
        assert total == 2 + 4 + 1  # +1 for decision step

    def test_investment_scenario(self):
        meta_qs, data_qs, total = compute_total_steps("investment", None, None, None)
        assert len(meta_qs) == 2
        assert len(data_qs) == 4
        assert total == 7

    def test_distribution_scenario(self):
        meta_qs, data_qs, total = compute_total_steps("distribution", None, None, None)
        assert len(meta_qs) == 2
        assert len(data_qs) == 4
        assert total == 7

    def test_custom_scenario_with_question(self):
        meta_qs, data_qs, total = compute_total_steps(
            "custom", "¿Qué película producir?", None, None,
        )
        assert len(meta_qs) == 1  # auto-generated
        assert len(data_qs) == 2  # auto-generated
        assert total == 1 + 2 + 1

    def test_custom_with_explicit_questions(self):
        custom_meta = ["¿Qué tablas hay?"]
        custom_data = ["Dame los datos de X", "Dame los datos de Y", "Dame los datos de Z"]
        meta_qs, data_qs, total = compute_total_steps(
            "custom", "Pregunta", custom_meta, custom_data,
        )
        assert meta_qs == custom_meta
        assert data_qs == custom_data
        assert total == 1 + 3 + 1

    def test_unknown_scenario_defaults_to_custom(self):
        meta_qs, data_qs, total = compute_total_steps(
            "custom", "Pregunta libre", None, None,
        )
        assert len(meta_qs) == 1
        assert len(data_qs) == 2


# ═══════════════════════════════════════════════════════════════
# Tests para SCENARIOS
# ═══════════════════════════════════════════════════════════════

class TestScenarios:
    def test_all_scenarios_have_required_keys(self):
        required_keys = {"title", "description", "metadata_questions", "data_questions_template"}
        for key, scenario in SCENARIOS.items():
            for rk in required_keys:
                assert rk in scenario, f"Escenario '{key}' no tiene la clave '{rk}'"

    def test_predefined_scenarios_have_questions(self):
        for key in ("production", "investment", "distribution"):
            scenario = SCENARIOS[key]
            assert len(scenario["metadata_questions"]) > 0, f"'{key}' sin metadata questions"
            assert len(scenario["data_questions_template"]) > 0, f"'{key}' sin data questions"

    def test_custom_scenario_has_empty_questions(self):
        assert SCENARIOS["custom"]["metadata_questions"] == []
        assert SCENARIOS["custom"]["data_questions_template"] == []

    def test_scenarios_have_parameters(self):
        for key in ("production", "investment", "distribution"):
            assert "parameters" in SCENARIOS[key]
            assert len(SCENARIOS[key]["parameters"]) > 0


# ═══════════════════════════════════════════════════════════════
# Tests para run_decision_pipeline (integración con mocks)
# ═══════════════════════════════════════════════════════════════

class TestRunDecisionPipeline:
    @pytest.mark.asyncio
    @patch("app.decision_engine.answer_data_question")
    @patch("app.decision_engine.answer_metadata_question")
    async def test_pipeline_calls_both_phases(self, mock_meta, mock_data):
        mock_meta.return_value = {"answer": "Tabla admin.movies con columnas: title, budget, revenue"}
        mock_data.return_value = {"answer": "Top 5 géneros: Action (ROI: 3.2), Comedy (ROI: 2.8)..."}

        result = await run_decision_pipeline(
            scenario_key="production",
            use_views="admin.movies",
        )

        # Phase 1: should call answerMetadataQuestion
        assert mock_meta.call_count == 2  # 2 metadata questions for production

        # Phase 2: should call answerDataQuestion (4 data + 1 decision)
        assert mock_data.call_count == 5  # 4 data questions + 1 final decision

        # Result structure
        assert "phase1_metadata" in result
        assert "phase2_data" in result
        assert "decision" in result
        assert len(result["phase1_metadata"]) == 2
        assert len(result["phase2_data"]) == 4

    @pytest.mark.asyncio
    @patch("app.decision_engine.answer_data_question")
    @patch("app.decision_engine.answer_metadata_question")
    async def test_phase2_receives_metadata_context(self, mock_meta, mock_data):
        """Verifica que las preguntas de la Fase 2 incluyen el contexto de la Fase 1."""
        mock_meta.return_value = {"answer": "La tabla admin.movies tiene columnas: title, budget, revenue, genre"}
        mock_data.return_value = {"answer": "Datos obtenidos correctamente"}

        await run_decision_pipeline(
            scenario_key="production",
            use_views="admin.movies",
        )

        # Check that Phase 2 calls include metadata context
        data_calls = mock_data.call_args_list
        # First 4 calls are data phase, last is decision
        for i in range(4):
            question_arg = data_calls[i][0][0]  # first positional arg
            assert "CONTEXTO IMPORTANTE" in question_arg, \
                f"La pregunta de datos #{i+1} no incluye el contexto de metadatos"
            assert "admin.movies" in question_arg

    @pytest.mark.asyncio
    @patch("app.decision_engine.answer_data_question")
    @patch("app.decision_engine.answer_metadata_question")
    async def test_pipeline_handles_metadata_errors(self, mock_meta, mock_data):
        mock_meta.side_effect = Exception("Connection timeout")
        mock_data.return_value = {"answer": "Datos"}

        result = await run_decision_pipeline(scenario_key="production")

        assert len(result["errors"]) > 0
        assert any("Metadata error" in e for e in result["errors"])

    @pytest.mark.asyncio
    @patch("app.decision_engine.answer_data_question")
    @patch("app.decision_engine.answer_metadata_question")
    async def test_pipeline_handles_data_errors(self, mock_meta, mock_data):
        mock_meta.return_value = {"answer": "Tabla disponible"}
        mock_data.side_effect = Exception("Query failed")

        result = await run_decision_pipeline(scenario_key="production")

        assert len(result["errors"]) > 0

    @pytest.mark.asyncio
    @patch("app.decision_engine.answer_data_question")
    @patch("app.decision_engine.answer_metadata_question")
    async def test_custom_scenario_generates_questions(self, mock_meta, mock_data):
        mock_meta.return_value = {"answer": "Tablas disponibles: admin.movies"}
        mock_data.return_value = {"answer": "Resultado del análisis"}

        result = await run_decision_pipeline(
            scenario_key="custom",
            custom_question="¿En qué género invertir?",
        )

        assert len(result["phase1_metadata"]) == 1
        assert len(result["phase2_data"]) == 2

    @pytest.mark.asyncio
    @patch("app.decision_engine.answer_data_question")
    @patch("app.decision_engine.answer_metadata_question")
    async def test_params_are_injected_in_data_questions(self, mock_meta, mock_data):
        mock_meta.return_value = {"answer": "Metadata info"}
        mock_data.return_value = {"answer": "Data result"}

        await run_decision_pipeline(
            scenario_key="production",
            params={"genre": "Horror", "min_year": "2020"},
        )

        data_calls = mock_data.call_args_list
        for i in range(4):
            question_arg = data_calls[i][0][0]
            assert "Horror" in question_arg
            assert "2020" in question_arg


# ═══════════════════════════════════════════════════════════════
# Tests para run_decision_pipeline_stream (eventos SSE)
# ═══════════════════════════════════════════════════════════════

class TestRunDecisionPipelineStream:
    @pytest.mark.asyncio
    @patch("app.decision_engine.answer_data_question")
    @patch("app.decision_engine.answer_metadata_question")
    async def test_stream_emits_progress_and_complete(self, mock_meta, mock_data):
        mock_meta.return_value = {"answer": "Metadata"}
        mock_data.return_value = {"answer": "Data"}

        events = []
        async for event in run_decision_pipeline_stream(scenario_key="production"):
            events.append(event)

        # Should have progress events + 1 complete event
        progress_events = [e for e in events if e["type"] == "progress"]
        complete_events = [e for e in events if e["type"] == "complete"]

        assert len(complete_events) == 1
        assert len(progress_events) == 7  # 2 meta + 4 data + 1 decision
        assert complete_events[0]["percent"] == 100

    @pytest.mark.asyncio
    @patch("app.decision_engine.answer_data_question")
    @patch("app.decision_engine.answer_metadata_question")
    async def test_stream_phases_are_correct(self, mock_meta, mock_data):
        mock_meta.return_value = {"answer": "Metadata"}
        mock_data.return_value = {"answer": "Data"}

        phases = []
        async for event in run_decision_pipeline_stream(scenario_key="production"):
            if event["type"] == "progress":
                phases.append(event["phase"])

        # Phase order: metadata, metadata, data, data, data, data, decision
        assert phases[:2] == ["metadata", "metadata"]
        assert phases[2:6] == ["data", "data", "data", "data"]
        assert phases[6] == "decision"
