# DecisionLens — Herramienta de Toma de Decisiones con Denodo AI SDK

**HackUDC 2026 — Reto Denodo**

## ¿Qué es?

DecisionLens es una herramienta analítica de toma de decisiones que utiliza el **Denodo AI SDK** para investigar datos de forma autónoma y ofrecer recomendaciones fundamentadas en datos reales.

**No es un chatbot conversacional** — es una herramienta estructurada que implementa un proceso de razonamiento en dos fases obligatorias usando los endpoints del AI SDK.

## Arquitectura

```
┌─────────────────────────────────────────────┐
│            DecisionLens (Frontend)          │
│         HTML/CSS/JS — Puerto 5000           │
└──────────────────┬──────────────────────────┘
                   │
┌──────────────────▼──────────────────────────┐
│         DecisionLens API (FastAPI)          │
│         Motor de decisiones 2 fases         │
└──────────────────┬──────────────────────────┘
                   │
┌──────────────────▼──────────────────────────┐
│           Denodo AI SDK (8008)              │
│  /answerMetadataQuestion  │  /answerDataQ.  │
└──────────────────┬──────────────────────────┘
                   │
┌──────────────────▼──────────────────────────┐
│     Denodo Platform (Design Studio/DC)      │
│        Dataset: Full TMDB Movies 2024       │
└─────────────────────────────────────────────┘
```

## Flujo de decisión (2 fases obligatorias)

### Fase 1 — Análisis de metadatos (`/answerMetadataQuestion`)
El sistema consulta al Data Marketplace para descubrir qué información está disponible. Se adapta dinámicamente al dataset sin conocer los nombres de antemano.

### Fase 2 — Ejecución de consultas (`/answerDataQuestion`)
Con la estructura descubierta, el sistema genera consultas específicas para extraer datos concretos que fundamenten la decisión.

### Fase 3 — Recomendación final
Combina todos los hallazgos para generar una decisión concreta con:
- Recomendación específica
- Datos que la justifican (cifras)
- Riesgos a considerar
- Plan de acción

## Escenarios de decisión incluidos

| Escenario | Descripción |
|-----------|-------------|
| 🎬 Producción | ¿Qué tipo de película debería producir una productora? |
| 💰 Inversión | ¿En qué tipo de películas conviene invertir? |
| 🌍 Distribución | ¿En qué mercado/idioma distribuir una película? |
| 🔍 Personalizado | Define tu propio escenario de decisión |

## Requisitos previos

1. **Docker** corriendo con los contenedores de Denodo:
   ```bash
   cd ~/informatica/Denodo_Enviroment
   docker compose up -d
   ```

2. **Dataset cargado** en Denodo Design Studio (TMDB Movies)

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

## Endpoints de la API

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/` | Interfaz web principal |
| GET | `/api/health` | Estado de la conexión con Denodo |
| GET | `/api/scenarios` | Lista de escenarios disponibles |
| POST | `/api/decide` | Ejecuta pipeline completo de decisión |
| POST | `/api/ask` | Pregunta libre a los endpoints del SDK |

## Estructura del proyecto

```
Proyecto-HackUDC-2026/
├── app/
│   ├── __init__.py
│   ├── main.py              # API FastAPI
│   ├── denodo_client.py     # Cliente Denodo AI SDK
│   ├── decision_engine.py   # Motor de decisiones (2 fases)
│   ├── static/
│   │   ├── style.css        # Estilos
│   │   └── app.js           # Lógica frontend
│   └── templates/
│       └── index.html        # Página principal
├── run.py                    # Punto de entrada
├── requirements.txt          # Dependencias Python
├── .env                      # Configuración
└── README.md
```

## Tecnologías

- **Backend**: Python, FastAPI, httpx
- **Frontend**: HTML5, CSS3, JavaScript vanilla
- **Integración**: Denodo AI SDK (endpoints REST)
- **LLM**: Google AI Studio (gemma-3-27b-it)
- **Datos**: Denodo Platform (Design Studio + Data Marketplace)
