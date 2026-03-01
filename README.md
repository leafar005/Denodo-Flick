# Denodo Flick — Herramienta de Toma de Decisiones con Denodo AI SDK

**HackUDC 2026 — Reto Denodo**

## ¿Qué es?

Denodo Flick es una herramienta analítica de toma de decisiones que utiliza el **Denodo AI SDK** para investigar datos de forma autónoma y ofrecer recomendaciones fundamentadas en datos reales.

**No es un chatbot conversacional** — es una herramienta estructurada que implementa un proceso de razonamiento en dos fases obligatorias usando los endpoints del AI SDK.

## Arquitectura

```
┌─────────────────────────────────────────────┐
│            Denodo Flick (Frontend)          │
│         HTML/CSS/JS — Puerto 5000           │
└──────────────────┬──────────────────────────┘
                   │
┌──────────────────▼──────────────────────────┐
│         Denodo Flick API (FastAPI)          │
│         Motor de decisiones 2 fases         │
│  ┌───────────────────────────────────────┐  │
│  │  Fase 1 → descubre estructura         │  │
│  │  Fase 1 contexto → inyecta en Fase 2  │  │
│  │  Fase 2 → consultas informadas        │  │
│  │  Fase 3 → síntesis y recomendación    │  │
│  └───────────────────────────────────────┘  │
└──────────────────┬──────────────────────────┘
                   │
┌──────────────────▼──────────────────────────┐
│           Denodo AI SDK (8008)              │
│  /answerMetadataQuestion  │  /answerDataQ.  │
│  /getMetadata             │  /health        │
└──────────────────┬──────────────────────────┘
                   │
┌──────────────────▼──────────────────────────┐
│     Denodo Platform (Design Studio/DC)      │
│           Data Marketplace                  │
└─────────────────────────────────────────────┘
```

## Flujo de decisión (2 fases obligatorias + síntesis)

### Fase 1 — Análisis de metadatos (`/answerMetadataQuestion`)
El sistema consulta al Data Marketplace para descubrir qué tablas, columnas y relaciones existen. Se adapta dinámicamente al dataset sin conocer los nombres de antemano.

### Fase 2 — Ejecución de consultas informadas (`/answerDataQuestion`)
Con la estructura descubierta en la Fase 1, el sistema **inyecta el contexto de metadatos** en cada consulta de datos. De este modo, las consultas VQL se generan usando los nombres reales de tablas y columnas descubiertos, no asumidos. Esto garantiza que la Fase 2 está *basada en los hallazgos de la Fase 1* como exige el reto.

**Ejemplo del flujo:**
1. **Fase 1** descubre: *"La tabla `admin.movies` contiene columnas: title, budget, revenue, genre, vote_average"*
2. **Fase 2** recibe cada pregunta precedida por: *"CONTEXTO — Estructura descubierta: [info de Fase 1]. Usa EXCLUSIVAMENTE las tablas y columnas reales. Pregunta: ¿Cuáles son los 5 géneros con mejor ROI?"*
3. El AI SDK genera la consulta VQL usando las columnas reales descubiertas.

### Fase 3 — Recomendación final
Combina todos los hallazgos para generar una decisión concreta con:
- Recomendación específica
- Datos que la justifican (cifras reales)
- Riesgos a considerar
- Plan de acción

## Adaptación dinámica a cualquier dataset

Denodo FLick está diseñado para funcionar con **cualquier dataset** cargado en Denodo, no solo con un conjunto de datos específico:

- **Descubrimiento de vistas dinámico**: El selector de vistas en la interfaz permite escribir cualquier nombre de vista (`database.tabla`) y tiene un botón de descubrimiento automático (⚡) que consulta al AI SDK para listar las vistas disponibles en el Data Marketplace.
- **Fase 1 explora sin hardcodeo**: Las preguntas de metadatos descubren la estructura del dataset sea cual sea.
- **Fase 2 se adapta**: Las consultas se enriquecen con el contexto real descubierto, lo que permite que funcionen con tablas y columnas que no se conocían de antemano.
- **Escenario personalizado**: El modo "custom" permite definir cualquier decisión y el sistema genera automáticamente las preguntas de exploración y datos.

## Escenarios de decisión incluidos

| Escenario | Descripción |
|-----------|-------------|
| 🎬 Producción | ¿Qué tipo de película debería producir una productora? |
| 💰 Inversión | ¿En qué tipo de películas conviene invertir? |
| 🌍 Distribución | ¿En qué mercado/idioma distribuir una película? |
| 🔍 Personalizado | Define tu propio escenario de decisión |

Cada escenario incluye parámetros configurables (género, presupuesto, año, etc.) que refinan las consultas de datos.

## Requisitos previos

1. **Docker** corriendo con los contenedores de Denodo:
   ```bash
   cd ~/informatica/Denodo_Enviroment
   docker compose up -d
   ```

2. **Dataset cargado** en Denodo Design Studio

3. **Data Marketplace sincronizado** con las vistas creadas

4. **Python 3.11+**

## Instalación y ejecución

```bash
# Instalar dependencias
pip install -r requirements.txt

# Ejecutar la aplicación
python run.py
```

Abrir **http://localhost:5000** en el navegador.

## Tests

El proyecto incluye una suite de tests unitarios y de integración con 61 tests que cubren:

- **Motor de decisiones** (`test_decision_engine.py`): Lógica de 2 fases, inyección de contexto Fase 1→2, generación dinámica de preguntas, manejo de errores.
- **Cliente Denodo** (`test_denodo_client.py`): Comunicación con endpoints del AI SDK, limpieza de disclaimers, parsing de errores.
- **API REST** (`test_api.py`): Todos los endpoints HTTP, incluyendo el descubrimiento dinámico de vistas.

```bash
# Ejecutar todos los tests
python -m pytest tests/ -v

# Ejecutar solo tests del motor de decisiones
python -m pytest tests/test_decision_engine.py -v
```

## Endpoints de la API

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/` | Interfaz web principal |
| GET | `/api/health` | Estado de la conexión con Denodo AI SDK |
| GET | `/api/scenarios` | Lista de escenarios disponibles |
| GET | `/api/scenarios/{key}` | Detalle de un escenario (preguntas, parámetros) |
| POST | `/api/decide` | Ejecuta pipeline completo de decisión |
| POST | `/api/decide-stream` | Pipeline con streaming SSE de progreso |
| POST | `/api/sync-metadata` | Sincroniza metadatos del Data Marketplace |
| GET | `/api/discover-views` | Descubre dinámicamente las vistas disponibles |
| POST | `/api/ask` | Pregunta libre a los endpoints del SDK |

## Estructura del proyecto

```
Denodo-Flick/
├── app/
│   ├── __init__.py
│   ├── main.py              # API FastAPI + endpoints REST
│   ├── denodo_client.py     # Cliente Denodo AI SDK (HTTP)
│   ├── decision_engine.py   # Motor de decisiones (2 fases + síntesis)
│   ├── static/
│   │   ├── style.css        # Estilos (light/dark mode)
│   │   └── app.js           # Lógica frontend + descubrimiento dinámico
│   └── templates/
│       └── index.html        # Página principal
├── tests/
│   ├── __init__.py
│   ├── test_decision_engine.py  # Tests del motor de decisiones
│   ├── test_denodo_client.py    # Tests del cliente SDK
│   └── test_api.py              # Tests de integración API
├── run.py                    # Punto de entrada
├── requirements.txt          # Dependencias Python
├── .env                      # Configuración (opcional)
└── README.md
```

## Tecnologías

- **Backend**: Python 3.11+, FastAPI, httpx (async)
- **Frontend**: HTML5, CSS3, JavaScript vanilla
- **Integración**: Denodo AI SDK (endpoints REST con HTTP Basic Auth)
- **LLM**: Google AI Studio (gemma-3-27b-it / gemini)
- **Datos**: Denodo Platform (Design Studio + Data Marketplace)
- **Tests**: pytest, pytest-asyncio
