"""
API principal - Herramienta de Toma de Decisiones con Denodo AI SDK
HackUDC 2026 - Reto Denodo
"""

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel
from app.decision_engine import run_decision_pipeline, run_decision_pipeline_stream, SCENARIOS
from app.denodo_client import check_health, answer_metadata_question, answer_data_question, get_metadata
import os
import json

app = FastAPI(
    title="Denodo Flick - Denodo Decision Tool",
    description="Herramienta de toma de decisiones basada en datos usando Denodo AI SDK",
    version="1.0.0",
)

# Static files & templates
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))


# ── Modelos Pydantic ─────────────────────────────────────────────────

class DecisionRequest(BaseModel):
    scenario: str  # 'production', 'investment', 'distribution', 'custom'
    custom_question: str | None = None
    custom_metadata_questions: list[str] | None = None
    custom_data_questions: list[str] | None = None
    use_views: str | None = None  # ej: 'admin.p_movies' o 'admin.movies'
    parameters: dict | None = None  # parámetros específicos del escenario


class FreeQuestionRequest(BaseModel):
    question: str
    phase: str = "data"
    use_views: str | None = None


# ── Rutas de la interfaz web ─────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Página principal con los escenarios de decisión."""
    return templates.TemplateResponse("index.html", {
        "request": request,
        "scenarios": SCENARIOS,
    })


# ── API Endpoints ────────────────────────────────────────────────────

@app.get("/api/health")
async def health():
    """Estado de la aplicación y conexión con Denodo AI SDK."""
    health_info = await check_health()
    return {
        "app": "ok",
        "denodo_ai_sdk": "connected" if health_info["status"] else "disconnected",
        "details": health_info.get("data"),
    }


@app.get("/api/scenarios")
async def get_scenarios():
    """Lista los escenarios de decisión disponibles."""
    return {
        key: {"title": s["title"], "description": s["description"]}
        for key, s in SCENARIOS.items()
    }


@app.get("/api/scenarios/{key}")
async def get_scenario_detail(key: str):
    """Devuelve los detalles completos de un escenario, incluidas las preguntas."""
    scenario = SCENARIOS.get(key)
    if not scenario:
        return {"error": "Escenario no encontrado"}
    return {
        "key": key,
        "title": scenario["title"],
        "description": scenario["description"],
        "metadata_questions": scenario["metadata_questions"],
        "data_questions": scenario["data_questions_template"],
        "parameters": scenario.get("parameters", []),
    }


@app.post("/api/sync-metadata")
async def sync_metadata(database_names: str = ""):
    """
    Carga/sincroniza los metadatos del Data Marketplace en el vector store del AI SDK.
    Debe ejecutarse después de sincronizar el Data Marketplace.
    """
    try:
        result = await get_metadata(database_names)
        return {"status": "ok", "result": result}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.post("/api/decide")
async def decide(req: DecisionRequest):
    """
    Ejecuta el pipeline completo de decisión en 2 fases:
    1. answerMetadataQuestion → Descubre estructura de datos
    2. answerDataQuestion → Extrae datos concretos
    3. Genera recomendación final fundamentada
    """
    result = await run_decision_pipeline(
        scenario_key=req.scenario,
        custom_question=req.custom_question,
        custom_metadata_qs=req.custom_metadata_questions,
        custom_data_qs=req.custom_data_questions,
        use_views=req.use_views,
        params=req.parameters,
    )
    return result


@app.post("/api/decide-stream")
async def decide_stream(req: DecisionRequest):
    """
    Ejecuta el pipeline de decisión con streaming SSE de progreso.
    Emite eventos 'progress' con porcentaje y un evento 'complete' al finalizar.
    """
    async def event_generator():
        async for event in run_decision_pipeline_stream(
            scenario_key=req.scenario,
            custom_question=req.custom_question,
            custom_metadata_qs=req.custom_metadata_questions,
            custom_data_qs=req.custom_data_questions,
            use_views=req.use_views,
            params=req.parameters,
        ):
            yield f"event: {event['type']}\ndata: {json.dumps(event, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/api/discover-views")
async def discover_views():
    """
    Descubre dinámicamente las vistas/tablas disponibles en el Data Marketplace.
    Usa answerMetadataQuestion para explorar el entorno sin hardcodeo.
    """
    try:
        response = await answer_metadata_question(
            "List all available views"
        )
        # El SDK devuelve tables_used con la lista de vistas directamente
        views = []
        if isinstance(response, dict):
            # Extraer de tables_used si existe
            tables_used = response.get("tables_used", [])
            if tables_used:
                views = [t for t in tables_used if "." in t]

            # Fallback: intentar parsear del campo answer si es texto
            if not views:
                answer_text = response.get("answer", "")
                if isinstance(answer_text, str) and answer_text:
                    import re
                    matches = re.findall(r'\b(\w+\.\w+)\b', answer_text)
                    views = list(dict.fromkeys(m for m in matches
                        if len(m.split(".")[0]) > 1 and len(m.split(".")[1]) > 1))

        return {
            "status": "ok",
            "views": views,
            "answer": response.get("answer", "") if isinstance(response, dict) else str(response),
            "raw": response,
        }
    except Exception as e:
        return {"status": "error", "error": str(e), "views": []}


@app.post("/api/ask")
async def ask_free(req: FreeQuestionRequest):
    """
    Permite hacer preguntas libres a cualquiera de los 2 endpoints.
    Útil para exploración interactiva.
    """
    try:
        if req.phase == "metadata":
            response = await answer_metadata_question(req.question, use_views=req.use_views)
        else:
            response = await answer_data_question(req.question, use_views=req.use_views)
        return {"answer": response.get("answer", response), "raw": response}
    except Exception as e:
        return {"answer": None, "error": str(e)}
