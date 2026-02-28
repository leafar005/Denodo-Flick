"""
Motor de decisiones - Lógica de 2 fases obligatorias del reto Denodo HackUDC.

Fase 1: Análisis de metadatos (answerMetadataQuestion)
  → Descubre qué tablas/columnas existen en el dataset TMDB.

Fase 2: Ejecución de consultas (answerDataQuestion)
  → Extrae datos concretos para fundamentar la decisión.

Fase 3: Síntesis y recomendación final
  → Combina los hallazgos y genera una decisión fundamentada.
"""

from app.denodo_client import answer_metadata_question, answer_data_question
import json

# Opciones de género basadas en TMDB
GENRE_OPTIONS = [
    "Action", "Adventure", "Animation", "Comedy", "Crime", "Documentary",
    "Drama", "Family", "Fantasy", "History", "Horror", "Music",
    "Mystery", "Romance", "Science Fiction", "Thriller", "War", "Western",
]

LANGUAGE_OPTIONS = [
    {"value": "en", "label": "Inglés (en)"},
    {"value": "es", "label": "Español (es)"},
    {"value": "fr", "label": "Francés (fr)"},
    {"value": "de", "label": "Alemán (de)"},
    {"value": "ja", "label": "Japonés (ja)"},
    {"value": "ko", "label": "Coreano (ko)"},
    {"value": "zh", "label": "Chino (zh)"},
    {"value": "hi", "label": "Hindi (hi)"},
    {"value": "pt", "label": "Portugués (pt)"},
    {"value": "it", "label": "Italiano (it)"},
    {"value": "ru", "label": "Ruso (ru)"},
]

# ──────────────────────────────────────────────────────────────────────
# Escenarios de decisión predefinidos para el dataset TMDB
# ──────────────────────────────────────────────────────────────────────

SCENARIOS = {
    "production": {
        "title": "🎬 ¿Qué película debería producir una productora?",
        "description": "Analiza géneros, presupuestos, ingresos y ratings para recomendar qué tipo de película producir y maximizar el retorno de inversión.",
        "metadata_questions": [
            "¿Qué tablas y columnas contienen información sobre películas, incluyendo géneros, presupuesto (budget), ingresos (revenue), puntuación (vote_average) y popularidad?",
            "¿Qué columnas indican el idioma original, el país de producción y la fecha de estreno de las películas?",
        ],
        "data_questions_template": [
            "¿Cuáles son los 10 géneros de películas con mayor ingreso (revenue) promedio? Muestra el género, el revenue promedio, el budget promedio y el número de películas.",
            "¿Cuáles son los 5 géneros con mejor ratio revenue/budget (retorno de inversión)? Considera solo películas con budget mayor a 1000000.",
            "¿Cuáles son las 10 películas más rentables (mayor diferencia entre revenue y budget) de los últimos 5 años? Muestra título, género, budget, revenue y beneficio.",
            "¿Cuál es la puntuación media (vote_average) y popularidad media por género para películas de los últimos 3 años?",
        ],
        "parameters": [
            {"key": "genre", "label": "Género preferido", "type": "select", "options": GENRE_OPTIONS},
            {"key": "budget_range", "label": "Rango de presupuesto", "type": "select", "options": ["Bajo (< 5M $)", "Medio (5M - 50M $)", "Alto (> 50M $)"]},
            {"key": "min_year", "label": "Año mínimo de referencia", "type": "text", "placeholder": "Ej: 2015"},
            {"key": "min_rating", "label": "Rating mínimo (vote_average)", "type": "text", "placeholder": "Ej: 6.0"},
        ],
    },
    "investment": {
        "title": "💰 ¿En qué tipo de películas invertir?",
        "description": "Determina las mejores oportunidades de inversión cinematográfica basándote en tendencias de mercado, ROI histórico y demanda del público.",
        "metadata_questions": [
            "¿Qué tablas contienen datos de presupuesto (budget), ingresos (revenue), popularidad y valoración de películas?",
            "¿Existen columnas sobre compañías de producción, países de producción o información temporal de las películas?",
        ],
        "data_questions_template": [
            "¿Cuáles son los géneros con tendencia de crecimiento en los últimos años? Compara el número de películas y revenue promedio por género entre películas antiguas y recientes.",
            "¿Cuáles son las productoras con mejor track record de rentabilidad? Muestra las 10 productoras con mejor ratio revenue/budget promedio.",
            "¿Qué rangos de presupuesto (bajo <5M, medio 5-50M, alto >50M) tienen mejor retorno de inversión? Muestra el ROI promedio por rango.",
            "¿Cuáles son las películas con mayor puntuación y popularidad que tuvieron un presupuesto bajo (menor a 10 millones)?",
        ],
        "parameters": [
            {"key": "genre", "label": "Género de interés", "type": "select", "options": GENRE_OPTIONS},
            {"key": "budget_range", "label": "Rango de inversión", "type": "select", "options": ["Bajo (< 5M $)", "Medio (5M - 50M $)", "Alto (> 50M $)"]},
            {"key": "min_year", "label": "Año mínimo de referencia", "type": "text", "placeholder": "Ej: 2015"},
            {"key": "min_popularity", "label": "Popularidad mínima", "type": "text", "placeholder": "Ej: 10"},
        ],
    },
    "distribution": {
        "title": "🌍 ¿En qué mercado/idioma distribuir una película?",
        "description": "Analiza el rendimiento por idioma y mercado para decidir dónde distribuir o en qué idioma producir contenido.",
        "metadata_questions": [
            "¿Qué tablas y columnas contienen información sobre el idioma original de las películas, el país de producción y los ingresos?",
            "¿Qué datos hay disponibles sobre la popularidad y recepción de películas por idioma o región?",
        ],
        "data_questions_template": [
            "¿Cuáles son los 10 idiomas con mayor ingreso (revenue) total y promedio por película?",
            "¿Cuáles son los idiomas con películas mejor puntuadas (vote_average) en promedio? Muestra los 10 principales.",
            "¿Cuál es la tendencia de producción por idioma en los últimos años? ¿Qué idiomas están creciendo más?",
            "Para películas en idiomas distintos al inglés, ¿cuáles tienen mejor rendimiento comercial (revenue) y de crítica (vote_average)?",
        ],
        "parameters": [
            {"key": "genre", "label": "Género de la película", "type": "select", "options": GENRE_OPTIONS},
            {"key": "language", "label": "Idioma de la película", "type": "select", "options": [l["label"] for l in LANGUAGE_OPTIONS]},
            {"key": "budget_range", "label": "Rango de presupuesto", "type": "select", "options": ["Bajo (< 5M $)", "Medio (5M - 50M $)", "Alto (> 50M $)"]},
            {"key": "min_year", "label": "Año mínimo de referencia", "type": "text", "placeholder": "Ej: 2015"},
        ],
    },
    "custom": {
        "title": "🔍 Decisión personalizada",
        "description": "Define tu propio escenario de decisión. El sistema explorará los datos disponibles y te dará una recomendación fundamentada.",
        "metadata_questions": [],
        "data_questions_template": [],
        "parameters": [],
    },
}


def build_param_context(params: dict | None) -> str:
    """Construye un contexto textual a partir de los parámetros del usuario."""
    if not params:
        return ""

    filters = []
    if params.get("genre"):
        filters.append(f"género '{params['genre']}'")
    if params.get("budget_range"):
        filters.append(f"rango de presupuesto {params['budget_range']}")
    if params.get("min_year"):
        filters.append(f"considerando solo películas desde el año {params['min_year']}")
    if params.get("min_rating"):
        filters.append(f"con rating mínimo de {params['min_rating']}")
    if params.get("language"):
        filters.append(f"idioma '{params['language']}'")
    if params.get("min_popularity"):
        filters.append(f"con popularidad mínima de {params['min_popularity']}")

    if not filters:
        return ""

    return " Filtra y enfoca el análisis considerando estos parámetros del usuario: " + ", ".join(filters) + "."


async def run_decision_pipeline(
    scenario_key: str,
    custom_question: str | None = None,
    custom_metadata_qs: list[str] | None = None,
    custom_data_qs: list[str] | None = None,
    use_views: str | None = None,
    params: dict | None = None,
) -> dict:
    """
    Ejecuta el pipeline completo de decisión en 2 fases.
    Retorna un dict con los resultados de cada fase y la decisión final.
    """
    scenario = SCENARIOS.get(scenario_key, SCENARIOS["custom"])
    results = {
        "scenario": scenario["title"],
        "description": scenario["description"],
        "phase1_metadata": [],
        "phase2_data": [],
        "decision": None,
        "errors": [],
    }

    # ── FASE 1: Análisis de metadatos ──────────────────────────────────
    metadata_questions = custom_metadata_qs or scenario["metadata_questions"]

    if scenario_key == "custom" and custom_question and not metadata_questions:
        # Generar preguntas de metadatos a partir de la pregunta personalizada
        metadata_questions = [
            f"¿Qué tablas y columnas disponibles en el Data Marketplace están relacionadas con: {custom_question}? Describe la estructura de datos relevante.",
        ]

    for mq in metadata_questions:
        try:
            response = await answer_metadata_question(mq, use_views=use_views)
            results["phase1_metadata"].append({
                "question": mq,
                "answer": response.get("answer", response),
                "raw": response,
            })
        except Exception as e:
            results["phase1_metadata"].append({
                "question": mq,
                "answer": None,
                "error": str(e),
            })
            results["errors"].append(f"Metadata error: {str(e)}")

    # ── Construir contexto de la fase 1 para informar fase 2 ──────────
    metadata_context = "\n".join(
        f"- {item['answer']}" for item in results["phase1_metadata"]
        if item.get("answer")
    )

    # ── FASE 2: Ejecución de consultas de datos ───────────────────────
    data_questions = custom_data_qs or scenario["data_questions_template"]

    if scenario_key == "custom" and custom_question and not data_questions:
        data_questions = [
            f"Basándote en los datos disponibles, {custom_question}. Proporciona datos concretos y cifras.",
            f"¿Cuáles son las mejores opciones considerando: {custom_question}? Compara al menos 3 alternativas con datos numéricos.",
        ]

    param_context = build_param_context(params)

    for dq in data_questions:
        dq_final = dq + param_context if param_context else dq
        try:
            response = await answer_data_question(dq_final, use_views=use_views)
            results["phase2_data"].append({
                "question": dq,
                "answer": response.get("answer", response),
                "raw": response,
            })
        except Exception as e:
            results["phase2_data"].append({
                "question": dq,
                "answer": None,
                "error": str(e),
            })
            results["errors"].append(f"Data error: {str(e)}")

    # ── FASE 3: Generar decisión final ─────────────────────────────────
    data_context = "\n".join(
        f"- {item['answer']}" for item in results["phase2_data"]
        if item.get("answer")
    )

    if data_context:
        param_info = ""
        if params:
            param_parts = [f"{k}: {v}" for k, v in params.items() if v]
            if param_parts:
                param_info = f"\nPARÁMETROS ESPECÍFICOS DEL USUARIO: {', '.join(param_parts)}\n"

        decision_question = (
            f"Actúa como un analista experto. Basándote EXCLUSIVAMENTE en los siguientes datos reales extraídos:\n\n"
            f"CONTEXTO DE METADATOS:\n{metadata_context}\n\n"
            f"DATOS EXTRAÍDOS:\n{data_context}\n\n"
            f"{param_info}"
            f"Genera una RECOMENDACIÓN FINAL concreta y fundamentada para el siguiente escenario: {scenario['title']}. "
            f"La recomendación debe incluir:\n"
            f"1. La decisión concreta (qué hacer)\n"
            f"2. Los datos que la justifican (cifras específicas)\n"
            f"3. Los riesgos a considerar\n"
            f"4. Un plan de acción concreto\n"
            f"Sé específico y usa los números reales de los datos."
        )
        try:
            decision_response = await answer_data_question(decision_question, use_views=use_views)
            results["decision"] = decision_response.get("answer", decision_response)
        except Exception as e:
            results["decision"] = f"Error generando decisión: {str(e)}"
            results["errors"].append(f"Decision error: {str(e)}")
    else:
        results["decision"] = "No se pudieron obtener datos suficientes para generar una recomendación."

    return results
