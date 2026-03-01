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

# Formato común que se añade a todas las preguntas de estadísticas
_STAT_FMT = "Para cada elemento devuelve EXACTAMENTE una línea con el formato: nombre | valor_numérico. Sin encabezados, sin texto adicional, sin markdown."
_YEAR_FILTER = "Considera solo registros entre el año {min_year} y {max_year}. " 

STATISTICS_QUERIES = {
    "Géneros": {
        "questions": [
            f"Muestra los 12 géneros de películas con mayor popularidad promedio. {_STAT_FMT}",
            f"Muestra los 12 géneros de películas con mayor número de películas. {_STAT_FMT}",
        ],
        "charts": [
            {"type": "bar", "title": "Géneros más populares (popularidad media)", "color": "#6366f1"},
            {"type": "bar", "title": "Géneros con más películas", "color": "#f59e0b"},
        ],
    },
    "Películas": {
        "questions": [
            f"Muestra las 15 películas con mayor popularidad. Devuelve título y popularidad. {_STAT_FMT}",
            f"Muestra las 15 películas con mayor revenue (ingresos). Devuelve título y revenue. {_STAT_FMT}",
        ],
        "charts": [
            {"type": "horizontalBar", "title": "Películas más populares", "color": "#10b981"},
            {"type": "horizontalBar", "title": "Películas con más ingresos", "color": "#ef4444"},
        ],
    },
    "Series": {
        "questions": [
            f"Muestra las 15 series (type = 'SHOW') con mayor popularidad (tmdb_popularity). Devuelve título y tmdb_popularity. {_STAT_FMT}",
            f"Muestra las 15 series (type = 'SHOW') con mayor puntuación (imdb_score). Solo series con imdb_score > 0. Devuelve título e imdb_score. {_STAT_FMT}",
        ],
        "charts": [
            {"type": "horizontalBar", "title": "Series más populares", "color": "#8b5cf6"},
            {"type": "horizontalBar", "title": "Series mejor puntuadas (IMDb)", "color": "#ec4899"},
        ],
    },
    "Actores": {
        "questions": [
            f"Consulta la vista admin.actores. Muestra los 15 actores (primaryprofession que contenga 'actor' o 'actress') que aparecen en más títulos según la columna knownfortitles (cuenta los títulos separados por comas). Devuelve primaryname y el número de títulos. {_STAT_FMT}",
            f"Consulta la vista admin.actores. Muestra los 15 actores (primaryprofession que contenga 'actor' o 'actress') más veteranos que sigan vivos (deathyear es nulo o vacío). Devuelve primaryname y birthyear, ordenados por birthyear ascendente. {_STAT_FMT}",
        ],
        "charts": [
            {"type": "horizontalBar", "title": "Actores con más títulos", "color": "#14b8a6"},
            {"type": "bar", "title": "Actores veteranos aún vivos", "color": "#f97316"},
        ],
    },
}

# ── Mapping de vistas fijas por escenario ────────────────────────────
SCENARIO_VIEWS = {
    "production": "admin.movies",
    "series_production": "admin.netflix",
    "actor_recommendation": "admin.actores",
}


def resolve_scenario_view(scenario_key: str, params: dict | None = None) -> str | None:
    """
    Determina la vista fija que debe usar un escenario.
    Retorna None para 'custom' (el usuario elige con el selector).
    """
    if scenario_key in SCENARIO_VIEWS:
        return SCENARIO_VIEWS[scenario_key]

    if scenario_key in ("investment", "distribution"):
        ct = (params or {}).get("content_type", "Películas")
        return "admin.netflix" if ct == "Series" else "admin.movies"

    if scenario_key == "statistics":
        cat = (params or {}).get("stat_category", "Géneros")
        if cat == "Series":
            return "admin.netflix"
        elif cat == "Actores":
            return "admin.actores"
        else:  # Géneros, Películas
            return "admin.movies"

    return None  # custom — el usuario elige


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
        "title": "💰 ¿En qué contenido invertir?",
        "description": "Determina las mejores oportunidades de inversión en películas o series basándote en tendencias de mercado, ROI histórico y demanda del público.",
        "metadata_questions": [
            "¿Qué tablas contienen datos de presupuesto (budget), ingresos (revenue), popularidad y valoración de películas?",
            "¿Existen columnas sobre compañías de producción, países de producción o información temporal de las películas?",
        ],
        "metadata_questions_series": [
            "¿Qué tablas y columnas contienen información sobre series (type = 'SHOW'), incluyendo géneros, puntuación (imdb_score, tmdb_score), popularidad (tmdb_popularity), temporadas (seasons) y país de producción (production_countries)?",
            "¿Qué columnas indican el año de estreno, la duración (runtime), el país de producción y la clasificación por edades de las series?",
        ],
        "data_questions_template": [
            "¿Cuáles son los géneros con tendencia de crecimiento en los últimos años? Compara el número de películas y revenue promedio por género entre películas antiguas y recientes.",
            "¿Cuáles son las productoras con mejor track record de rentabilidad? Muestra las 10 productoras con mejor ratio revenue/budget promedio.",
            "¿Qué rangos de presupuesto (bajo <5M, medio 5-50M, alto >50M) tienen mejor retorno de inversión? Muestra el ROI promedio por rango.",
            "¿Cuáles son las películas con mayor puntuación y popularidad que tuvieron un presupuesto bajo (menor a 10 millones)?",
        ],
        "data_questions_series": [
            "¿Cuáles son los géneros de series (type = 'SHOW') con tendencia de crecimiento en los últimos años? Compara el número de series y la puntuación media (imdb_score) por género entre series antiguas y recientes.",
            "¿Cuáles son las 10 series (type = 'SHOW') con mejor combinación de puntuación (imdb_score > 7) y alta popularidad (tmdb_popularity)? Muestra título, género, imdb_score, tmdb_popularity, temporadas y año de estreno.",
            "¿Qué géneros de series ofrecen la mejor combinación de alta demanda (número de series + popularidad) y calidad (imdb_score)? Muestra los 5 mejores con métricas detalladas.",
            "¿Cuáles son las series con puntuaciones altas (imdb_score > 7.5) que podrían considerarse infravaloradas por tener baja popularidad? Muestra las 10 mejores con título, género, imdb_score, tmdb_popularity y temporadas.",
        ],
        "parameters": [
            {"key": "content_type", "label": "Tipo de contenido", "type": "select", "options": ["Películas", "Series"]},
            {"key": "genre", "label": "Género de interés", "type": "select", "options": GENRE_OPTIONS},
            {"key": "budget_range", "label": "Presupuesto máximo", "type": "range", "min": 0, "max": 300, "step": 5, "default": 150, "unit": "M $"},
            {"key": "min_year", "label": "Año mínimo de referencia", "type": "text", "placeholder": "Ej: 2015"},
            {"key": "min_popularity", "label": "Popularidad mínima", "type": "text", "placeholder": "Ej: 10"},
        ],
    },
    "distribution": {
        "title": "🌍 ¿En qué mercado distribuir?",
        "description": "Analiza el rendimiento por idioma y mercado para decidir dónde distribuir películas o series.",
        "metadata_questions": [
            "¿Qué tablas y columnas contienen información sobre el idioma original de las películas, el país de producción y los ingresos?",
            "¿Qué datos hay disponibles sobre la popularidad y recepción de películas por idioma o región?",
        ],
        "metadata_questions_series": [
            "¿Qué tablas y columnas contienen información sobre series (type = 'SHOW'), incluyendo géneros, puntuación (imdb_score, tmdb_score), popularidad (tmdb_popularity), país de producción (production_countries) y temporadas (seasons)?",
            "¿Existen datos sobre el país de producción, clasificación por edades y la popularidad de series?",
        ],
        "data_questions_template": [
            "¿Cuáles son los 10 idiomas con mayor ingreso (revenue) total y promedio por película?",
            "¿Cuáles son los idiomas con películas mejor puntuadas (vote_average) en promedio? Muestra los 10 principales.",
            "¿Cuál es la tendencia de producción por idioma en los últimos años? ¿Qué idiomas están creciendo más?",
            "Para películas en idiomas distintos al inglés, ¿cuáles tienen mejor rendimiento comercial (revenue) y de crítica (vote_average)?",
        ],
        "data_questions_series": [
            "¿Cuáles son los 10 países de producción (production_countries) con mayor número de series (type = 'SHOW') producidas y mayor puntuación media (imdb_score)? Muestra país, número de series, imdb_score promedio y tmdb_popularity promedio.",
            "¿Cuáles son los países de producción con series mejor puntuadas (imdb_score) en promedio? Muestra los 10 principales con número de series y popularidad media (tmdb_popularity).",
            "¿Cuál es la tendencia de producción de series (type = 'SHOW') por país de producción (production_countries) en los últimos años? ¿Qué países están creciendo más?",
            "Para series producidas fuera de EE.UU., ¿cuáles tienen mejor rendimiento (mayor tmdb_popularity e imdb_score)? Muestra las 10 principales con título, país de producción, imdb_score y tmdb_popularity.",
        ],
        "parameters": [
            {"key": "content_type", "label": "Tipo de contenido", "type": "select", "options": ["Películas", "Series"]},
            {"key": "genre", "label": "Género", "type": "select", "options": GENRE_OPTIONS},
            {"key": "language", "label": "Idioma", "type": "select", "options": [l["label"] for l in LANGUAGE_OPTIONS]},
            {"key": "budget_range", "label": "Presupuesto máximo", "type": "range", "min": 0, "max": 300, "step": 5, "default": 150, "unit": "M $"},
            {"key": "min_year", "label": "Año mínimo de referencia", "type": "text", "placeholder": "Ej: 2015"},
        ],
    },
    "actor_recommendation": {
        "title": "🎭 ¿Qué actor contratar para un género?",
        "description": "Recomienda los mejores actores para un género cinematográfico concreto, basándose en su historial de películas, puntuaciones, popularidad e ingresos en ese género.",
        "metadata_questions": [
            "¿Qué tablas y columnas contienen información sobre actores? Lista TODAS las columnas disponibles y sus tipos. Necesito saber si existe una columna con el NOMBRE del actor (por ejemplo primaryname, name, actor_name, title, o similar) y si existe alguna columna con el identificador (id, actor_id, nconst, etc.).",
            "¿Qué columnas contienen información sobre géneros (genres), puntuación (vote_average o popularity), ingresos (revenue o budget) y cualquier otro campo relevante para relacionar actores con películas?",
        ],
        "data_questions_template": [
            "¿Cuáles son los 15 actores con más películas en el género '{genre}'? OBLIGATORIO: muestra el NOMBRE COMPLETO del actor (no su ID numérico). Si la columna de nombre se llama primaryname, name, actor_name o title, úsala. Incluye: nombre del actor, número de películas en ese género y popularidad media. Filtra por actores cuya profesión contenga 'actor' o 'actress' si esa columna existe.",
            "¿Cuáles son los 15 actores con mayor popularidad media en películas del género '{genre}'? OBLIGATORIO: muestra el NOMBRE COMPLETO del actor (no su ID numérico). Incluye: nombre del actor, popularidad media y número de películas en ese género. Solo actores con al menos 2 películas en ese género.",
            "¿Cuáles son las 10 películas mejor valoradas (por popularidad) del género '{genre}' y qué actores participaron en ellas? OBLIGATORIO: muestra el NOMBRE del actor y el título de la película, NO IDs numéricos. Incluye: título de película, nombre del actor, popularidad y géneros.",
            "Para los actores más prolíficos en el género '{genre}', ¿cuál es la distribución de su trabajo en otros géneros? OBLIGATORIO: muestra NOMBRES de actores, no IDs. Muestra los 10 actores con más películas en '{genre}' y sus otros géneros frecuentes.",
        ],
        "parameters": [
            {"key": "genre", "label": "Género cinematográfico", "type": "select", "options": GENRE_OPTIONS},
            {"key": "min_movies", "label": "Mínimo de películas en el género", "type": "text", "placeholder": "Ej: 3"},
            {"key": "only_alive", "label": "Solo actores vivos", "type": "select", "options": ["Sí", "No"]},
            {"key": "min_popularity", "label": "Popularidad mínima", "type": "text", "placeholder": "Ej: 5"},
        ],
    },
    "statistics": {
        "title": "📊 Estadísticas del catálogo",
        "description": "Selecciona una categoría y un rango de años para visualizar los datos más destacados en gráficos interactivos.",
        "metadata_questions": [
            "¿Qué tablas y columnas contienen información sobre películas (título, género, presupuesto, ingresos, popularidad, puntuación), series (título, género, imdb_score, tmdb_popularity, temporadas) y actores (nombre, profesión, películas asociadas)?",
        ],
        "data_questions_template": [],  # se rellenan dinámicamente según stat_category
        "parameters": [
            {"key": "stat_category", "label": "Categoría", "type": "select", "options": ["Géneros", "Películas", "Series", "Actores"]},
            {"key": "min_year", "label": "Año desde", "type": "text", "placeholder": "Ej: 2000"},
            {"key": "max_year", "label": "Año hasta", "type": "text", "placeholder": "Ej: 2025"},
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
            f"\nIMPORTANTE: Consulta ÚNICAMENTE la vista {use_views}. "
            f"NO hagas JOIN ni consultes NINGUNA otra vista o tabla. "
            f"Solo usa columnas que existan en {use_views}. "
            f"Si un filtro menciona una columna que no existe en {use_views}, ignóralo.\n"
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
    is_series = params.get("content_type") == "Series"
    if params.get("content_type"):
        ct = params["content_type"]
        if ct == "Series":
            filters.append("analiza SOLO series (type = 'SHOW'), NO películas")
        else:
            filters.append("analiza SOLO películas, NO series")
    if params.get("genre"):
        filters.append(f"género '{params['genre']}'")
    if params.get("budget_range") and not is_series:
        filters.append(f"con presupuesto máximo de {params['budget_range']}")
    if params.get("min_year"):
        filters.append(f"considerando solo registros desde el año {params['min_year']}")
    if params.get("max_year"):
        filters.append(f"hasta el año {params['max_year']}")
    if params.get("min_rating"):
        filters.append(f"con rating mínimo de {params['min_rating']}")
    if params.get("language") and not is_series:
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

    # Investment/Distribution: usar plantillas de series si content_type es "Series"
    if scenario_key in ("investment", "distribution") and not custom_data_qs:
        if (params or {}).get("content_type") == "Series":
            if not custom_metadata_qs:
                metadata_questions = list(scenario.get("metadata_questions_series", scenario["metadata_questions"]))
            data_questions = list(scenario.get("data_questions_series", scenario["data_questions_template"]))

    # Estadísticas: seleccionar preguntas dinámicamente según la categoría
    if scenario_key == "statistics" and not custom_data_qs:
        cat = (params or {}).get("stat_category", "Géneros")
        stat_cfg = STATISTICS_QUERIES.get(cat, STATISTICS_QUERIES["Géneros"])
        year_prefix = ""
        min_y = (params or {}).get("min_year", "").strip()
        max_y = (params or {}).get("max_year", "").strip()
        if min_y or max_y:
            min_y = min_y or "1900"
            max_y = max_y or "2026"
            year_prefix = f"Considera solo registros entre el año {min_y} y {max_y}. "
        data_questions = [year_prefix + q for q in stat_cfg["questions"]]

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
    # Resolver vista fija del escenario (los predefinidos ignoran use_views del frontend)
    resolved_view = resolve_scenario_view(scenario_key, params)
    if resolved_view:
        use_views = resolved_view

    scenario = SCENARIOS.get(scenario_key, SCENARIOS["custom"])
    metadata_questions, data_questions, total_steps = compute_total_steps(
        scenario_key, custom_question, custom_metadata_qs, custom_data_qs, params,
    )

    results = {
        "scenario": scenario["title"],
        "scenario_key": scenario_key,
        "description": scenario["description"],
        "phase1_metadata": [],
        "phase2_data": [],
        "decision": None,
        "errors": [],
    }
    if scenario.get("chart_config"):
        results["chart_config"] = scenario["chart_config"]
    # Estadísticas: chart_config dinámico
    if scenario_key == "statistics":
        cat = (params or {}).get("stat_category", "Géneros")
        stat_cfg = STATISTICS_QUERIES.get(cat, STATISTICS_QUERIES["Géneros"])
        results["chart_config"] = stat_cfg["charts"]

    current_step = 0
    n_meta = len(metadata_questions)
    n_data = len(data_questions)

    # ── FASE 1: Análisis de metadatos ──────────────────────────────────
    # Si el usuario seleccionó vistas específicas, restringir las preguntas
    # de metadatos para que solo consideren esas vistas y evitar ambigüedades.
    view_restriction = ""
    if use_views:
        view_restriction = (
            f" Usa ÚNICAMENTE la vista {use_views}. "
            f"NO menciones, consultes ni hagas referencia a NINGUNA otra vista o tabla. "
            f"Solo describe las columnas y estructura de {use_views}. "
            f"Si algún campo no existe en {use_views}, ignóralo."
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
        # Inyectar nombre de vista directamente al inicio para evitar ambigüedad
        if use_views:
            mq_final = f"Describe SOLO la vista {use_views} (ignora todas las demás tablas): " + mq_final
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
        # Inyectar nombre de vista directamente en la pregunta para evitar ambigüedad
        if use_views:
            dq_final = f"Consultando SOLO la vista {use_views} (no uses ninguna otra tabla): " + dq_final
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
            f"IMPORTANTE: Usa SIEMPRE nombres propios de personas, películas, series o géneros. NUNCA muestres IDs numéricos en la recomendación; si los datos solo contienen IDs, indica que el nombre no está disponible en lugar de mostrar el ID. "
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
