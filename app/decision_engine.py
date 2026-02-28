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
            {"key": "budget_range", "label": "Presupuesto máximo", "type": "range", "min": 0, "max": 300, "step": 5, "default": 150, "unit": "M $"},
            {"key": "min_year", "label": "Año mínimo de referencia", "type": "text", "placeholder": "Ej: 2015"},
            {"key": "min_rating", "label": "Rating mínimo (vote_average)", "type": "text", "placeholder": "Ej: 6.0"},
        ],
    },
    "series_production": {
        "title": "📺 ¿Qué serie debería producir una productora?",
        "description": "Analiza géneros, puntuaciones, popularidad y temporadas de series para recomendar qué tipo de serie producir y maximizar el éxito.",
        "metadata_questions": [
            "¿Qué tablas y columnas contienen información sobre series (SHOW), incluyendo géneros, puntuación (imdb_score, tmdb_score), popularidad (tmdb_popularity), temporadas (seasons) y clasificación por edades?",
            "¿Qué columnas indican el año de estreno, la duración (runtime), el país de producción y la clasificación por edades de las series?",
        ],
        "data_questions_template": [
            "¿Cuáles son los 10 géneros de series (type = 'SHOW') con mayor puntuación media (imdb_score)? Muestra el género, el imdb_score promedio, el tmdb_score promedio, la popularidad promedio y el número de series.",
            "¿Cuáles son los 5 géneros de series con mayor popularidad (tmdb_popularity) promedio? Considera solo series con imdb_score mayor a 5.",
            "¿Cuáles son las 10 series (type = 'SHOW') mejor puntuadas (imdb_score) de los últimos 5 años? Muestra título, género, imdb_score, tmdb_score, temporadas y año de estreno.",
            "¿Cuál es la puntuación media (imdb_score) y la popularidad media (tmdb_popularity) por género para series (type = 'SHOW') estrenadas en los últimos 3 años?",
        ],
        "parameters": [
            {"key": "genre", "label": "Género preferido", "type": "select", "options": GENRE_OPTIONS},
            {"key": "min_seasons", "label": "Temporadas mínimas de referencia", "type": "text", "placeholder": "Ej: 2"},
            {"key": "min_year", "label": "Año mínimo de referencia", "type": "text", "placeholder": "Ej: 2018"},
            {"key": "min_rating", "label": "Rating mínimo (imdb_score)", "type": "text", "placeholder": "Ej: 7.0"},
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
            {"key": "budget_range", "label": "Presupuesto máximo", "type": "range", "min": 0, "max": 300, "step": 5, "default": 150, "unit": "M $"},
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
            {"key": "budget_range", "label": "Presupuesto máximo", "type": "range", "min": 0, "max": 300, "step": 5, "default": 150, "unit": "M $"},
            {"key": "min_year", "label": "Año mínimo de referencia", "type": "text", "placeholder": "Ej: 2015"},
        ],
    },
    "actor_recommendation": {
        "title": "🎭 ¿Qué actor contratar para un género?",
        "description": "Recomienda los mejores actores para un género cinematográfico concreto, basándose en su historial de películas, puntuaciones, popularidad e ingresos en ese género.",
        "metadata_questions": [
            "¿Qué tablas y columnas contienen información sobre actores, incluyendo su nombre (primaryname), profesión (primaryprofession), año de nacimiento (birthyear), año de fallecimiento (deathyear) y las películas en las que han participado (movie_id, movie_title)?",
            "¿Qué columnas de la tabla de actores contienen información sobre géneros (genres), puntuación (vote_average o popularity), ingresos (revenue o budget), sinopsis (overview), palabras clave (keywords) y compañías de producción (production_companies)?",
        ],
        "data_questions_template": [
            "¿Cuáles son los 15 actores con más películas en el género '{genre}'? Muestra el nombre del actor (primaryname), el número de películas en ese género, la popularidad media y el actor_id. Filtra por actores cuya primaryprofession contenga 'actor' o 'actress'.",
            "¿Cuáles son los 15 actores con mayor popularidad media en películas del género '{genre}'? Muestra primaryname, popularidad media, número de películas en ese género y actor_id. Solo actores con al menos 2 películas en ese género.",
            "¿Cuáles son las 10 películas mejor valoradas (por popularidad) del género '{genre}' y qué actores participaron en ellas? Muestra movie_title, primaryname, popularity y genres.",
            "Para los actores más prolíficos en el género '{genre}', ¿cuál es la distribución de su trabajo en otros géneros? Muestra los 10 actores con más películas en '{genre}' y sus otros géneros frecuentes.",
        ],
        "parameters": [
            {"key": "genre", "label": "Género cinematográfico", "type": "select", "options": GENRE_OPTIONS},
            {"key": "min_movies", "label": "Mínimo de películas en el género", "type": "text", "placeholder": "Ej: 3"},
            {"key": "only_alive", "label": "Solo actores vivos", "type": "select", "options": ["Sí", "No"]},
            {"key": "min_popularity", "label": "Popularidad mínima", "type": "text", "placeholder": "Ej: 5"},
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


def _build_metadata_prefix(metadata_context: str, use_views: str | None = None) -> str:
    """
    Construye un prefijo con el contexto descubierto en la Fase 1 para
    inyectarlo en cada pregunta de la Fase 2, de modo que las consultas
    de datos se basen en la estructura real del dataset.
    """
    if not metadata_context:
        return ""
    view_instruction = ""
    if use_views:
        view_instruction = (
            f"\nIMPORTANTE: Usa ÚNICAMENTE la(s) vista(s) {use_views}. "
            f"NO consultes ni hagas JOIN con otras vistas o tablas que no sean {use_views}.\n"
        )
    return (
        "CONTEXTO IMPORTANTE — Estructura de datos descubierta en la fase de análisis:\n"
        f"{metadata_context}\n\n"
        f"{view_instruction}"
        "Usa EXCLUSIVAMENTE las tablas y columnas reales descubiertas arriba para "
        "formular la consulta VQL. No preguntes por clarificaciones, genera directamente la consulta SQL/VQL. "
        "Pregunta concreta: "
    )


def build_param_context(params: dict | None) -> str:
    """Construye un contexto textual a partir de los parámetros del usuario."""
    if not params:
        return ""

    filters = []
    if params.get("genre"):
        filters.append(f"género '{params['genre']}'")
    if params.get("budget_range"):
        filters.append(f"con presupuesto máximo de {params['budget_range']}")
    if params.get("min_year"):
        filters.append(f"considerando solo películas desde el año {params['min_year']}")
    if params.get("min_rating"):
        filters.append(f"con rating mínimo de {params['min_rating']}")
    if params.get("language"):
        filters.append(f"idioma '{params['language']}'")
    if params.get("min_popularity"):
        filters.append(f"con popularidad mínima de {params['min_popularity']}")
    if params.get("min_seasons"):
        filters.append(f"con al menos {params['min_seasons']} temporadas")
    if params.get("min_movies"):
        filters.append(f"con al menos {params['min_movies']} películas en el género")
    if params.get("only_alive") and params["only_alive"] == "Sí":
        filters.append("solo actores vivos (deathyear vacío o nulo)")

    if not filters:
        return ""

    return " Filtra y enfoca el análisis considerando estos parámetros del usuario: " + ", ".join(filters) + "."


def compute_total_steps(
    scenario_key: str,
    custom_question: str | None,
    custom_metadata_qs: list[str] | None,
    custom_data_qs: list[str] | None,
    params: dict | None = None,
) -> tuple[list[str], list[str], int]:
    """
    Pre-calcula las preguntas de cada fase y el total de pasos para la barra de progreso.
    Retorna (metadata_questions, data_questions, total_steps).
    """
    scenario = SCENARIOS.get(scenario_key, SCENARIOS["custom"])
    metadata_questions = custom_metadata_qs or list(scenario["metadata_questions"])

    if scenario_key == "custom" and custom_question and not metadata_questions:
        metadata_questions = [
            f"¿Qué tablas y columnas disponibles en el Data Marketplace están relacionadas con: {custom_question}? Lista SOLO los nombres de columnas y sus tipos de datos.",
        ]

    data_questions = custom_data_qs or list(scenario["data_questions_template"])

    if scenario_key == "custom" and custom_question and not data_questions:
        data_questions = [
            f"Ejecuta una consulta para responder: {custom_question}. Devuelve los resultados con cifras numéricas reales de la base de datos. No pidas clarificaciones, interpreta 'beneficios' como la métrica más relevante disponible (revenue, imdb_score, popularidad, etc.).",
            f"Ejecuta una consulta que muestre un ranking o top de las mejores opciones para: {custom_question}. Incluye al menos 5 resultados con todas las métricas numéricas disponibles.",
        ]

    # Sustituir placeholders en las preguntas con los parámetros del usuario
    if params:
        subs = {k: v for k, v in params.items() if v}
        data_questions = [q.format_map(subs) if any(f"{{{k}}}" in q for k in subs) else q for q in data_questions]
        metadata_questions = [q.format_map(subs) if any(f"{{{k}}}" in q for k in subs) else q for q in metadata_questions]

    # +1 for the final decision generation step
    total = len(metadata_questions) + len(data_questions) + 1
    return metadata_questions, data_questions, total


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
    results = {}
    async for event in run_decision_pipeline_stream(
        scenario_key, custom_question, custom_metadata_qs,
        custom_data_qs, use_views, params,
    ):
        if event.get("type") == "complete":
            results = event["data"]
    return results


async def run_decision_pipeline_stream(
    scenario_key: str,
    custom_question: str | None = None,
    custom_metadata_qs: list[str] | None = None,
    custom_data_qs: list[str] | None = None,
    use_views: str | None = None,
    params: dict | None = None,
):
    """
    Generador asíncrono que ejecuta el pipeline y yield'ea eventos de progreso.
    Cada evento es un dict con: type, step, total, percent, phase, message, (data).
    """
    scenario = SCENARIOS.get(scenario_key, SCENARIOS["custom"])
    metadata_questions, data_questions, total_steps = compute_total_steps(
        scenario_key, custom_question, custom_metadata_qs, custom_data_qs, params,
    )

    results = {
        "scenario": scenario["title"],
        "description": scenario["description"],
        "phase1_metadata": [],
        "phase2_data": [],
        "decision": None,
        "errors": [],
    }

    current_step = 0
    n_meta = len(metadata_questions)
    n_data = len(data_questions)

    # ── FASE 1: Análisis de metadatos ──────────────────────────────────
    # Si el usuario seleccionó vistas específicas, restringir las preguntas
    # de metadatos para que solo consideren esas vistas y evitar ambigüedades.
    view_restriction = ""
    if use_views:
        view_restriction = (
            f" Analiza EXCLUSIVAMENTE la(s) vista(s): {use_views}. "
            f"NO incluyas información de otras vistas ni tablas. "
            f"Solo describe las columnas y estructura de {use_views}."
        )

    for i, mq in enumerate(metadata_questions, 1):
        current_step += 1
        percent = int(current_step / total_steps * 100)
        yield {
            "type": "progress",
            "step": current_step,
            "total": total_steps,
            "percent": percent,
            "phase": "metadata",
            "phase_step": i,
            "phase_total": n_meta,
            "message": f"Fase 1: Explorando metadatos ({i}/{n_meta})...",
        }
        mq_final = mq + view_restriction
        try:
            response = await answer_metadata_question(mq_final, use_views=use_views)
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
    # Inyectamos el contexto descubierto en la Fase 1 para que cada
    # consulta de datos se base en la estructura real encontrada.
    param_context = build_param_context(params)
    metadata_prefix = _build_metadata_prefix(metadata_context, use_views=use_views)

    for i, dq in enumerate(data_questions, 1):
        current_step += 1
        percent = int(current_step / total_steps * 100)
        yield {
            "type": "progress",
            "step": current_step,
            "total": total_steps,
            "percent": percent,
            "phase": "data",
            "phase_step": i,
            "phase_total": n_data,
            "message": f"Fase 2: Consultando datos ({i}/{n_data})...",
        }
        dq_final = metadata_prefix + dq + (param_context if param_context else "")
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
    current_step += 1
    percent = int(current_step / total_steps * 100)
    yield {
        "type": "progress",
        "step": current_step,
        "total": total_steps,
        "percent": percent,
        "phase": "decision",
        "phase_step": 1,
        "phase_total": 1,
        "message": "Fase 3: Generando recomendación final...",
    }

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

        view_hint = ""
        if use_views:
            view_hint = f"\nNOTA: Basa tu análisis SOLO en datos de la(s) vista(s) {use_views}. No consultes otras tablas.\n"

        decision_question = (
            f"Actúa como un analista experto. Basándote EXCLUSIVAMENTE en los siguientes datos reales extraídos:\n\n"
            f"CONTEXTO DE METADATOS:\n{metadata_context}\n\n"
            f"DATOS EXTRAÍDOS:\n{data_context}\n\n"
            f"{param_info}"
            f"{view_hint}"
            f"Genera una RECOMENDACIÓN FINAL concreta y fundamentada para el siguiente escenario: {scenario['title']}. "
            f"No pidas clarificaciones ni menciones ambigüedades, da directamente tu mejor recomendación. "
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

    # ── Evento final con todos los resultados ──────────────────────────
    yield {
        "type": "complete",
        "step": total_steps,
        "total": total_steps,
        "percent": 100,
        "phase": "done",
        "message": "Análisis completado",
        "data": results,
    }
