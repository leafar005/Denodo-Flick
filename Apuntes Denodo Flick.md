## 1. Visión General

**Denodo Flick** es una herramienta analítica de toma de decisiones desarrollada para el **HackUDC 2026** (reto de Denodo). No es un chatbot conversacional, sino un sistema estructurado que implementa un **pipeline de razonamiento en tres fases** utilizando los endpoints del **Denodo AI SDK** para investigar datos de forma autónoma en el **Data Marketplace** de Denodo y generar recomendaciones fundamentadas con datos reales.

El dominio de la aplicación se centra en la **industria del entretenimiento audiovisual**: producción de películas/series, inversión en contenido, distribución por mercados, contratación de actores y estadísticas de catálogo, usando datasets de **TMDB**, **Netflix**, **IMDb** y actores.

---

## 2. Arquitectura General

La arquitectura sigue un patrón **cliente-servidor de tres capas**:


$$\boxed{ \begin{array}{l} \text{\textbf{Frontend (index.html + app.js)}} \\ \text{Puerto 5000} \mid \text{Navegador del usuario} \end{array} }$$

$$\downarrow \text{ fetch / SSE (Server-Sent Events)}$$

$$\boxed{ \begin{array}{l} \text{\textbf{Backend FastAPI (main.py)}} \mid \text{Servidor Python (Uvicorn)} \\ \text{├── denodo\_client.py} \mid \text{Wrapper HTTP del AI SDK} \\ \text{└── decision\_engine.py} \mid \text{Motor de decisiones 3 fases} \end{array} }$$

$$\downarrow \text{ HTTP POST (Basic Auth)}$$

$$\boxed{ \begin{array}{l} \text{\textbf{Denodo AI SDK (puerto 8008)}} \mid \text{Docker container} \\ \text{├── /answerMetadataQuestion} \\ \text{├── /answerDataQuestion} \\ \text{├── /getMetadata} \\ \text{└── /health} \end{array} }$$

$$\downarrow \text{ VQL (Virtual Query Language)}$$

$$\boxed{ \begin{array}{l} \text{\textbf{Denodo Platform (Design Studio)}} \mid \text{Virtualización de datos} \\ \text{└── Data Marketplace} \end{array} }$$

---

## 3. El Pipeline de Decisión (Núcleo del Sistema)

El corazón de la aplicación es un **pipeline de razonamiento en 3 fases**, definido por el reto de Denodo:

### Fase 1 — Análisis de Metadatos (`answerMetadataQuestion`)

Antes de buscar datos, el sistema **descubre dinámicamente la estructura del entorno**: tablas, columnas, tipos de datos y relaciones. Esto permite que la aplicación se adapte a distintos datasets sin conocer sus nombres de antemano.

- **Endpoint del SDK**: `POST /answerMetadataQuestion`
- **Ejemplo**: *"¿Qué tablas y columnas contienen información sobre películas, incluyendo géneros, presupuesto, ingresos y puntuación?"*

### Fase 2 — Ejecución de Consultas (`answerDataQuestion`)

Con la estructura descubierta en la Fase 1 como **contexto inyectado**, el sistema ejecuta consultas VQL precisas para extraer datos concretos. El contexto de metadatos se prepende a cada pregunta para que el LLM genere consultas SQL/VQL correctas.

- **Endpoint del SDK**: `POST /answerDataQuestion`
- **Inyección de contexto**: La función `_build_metadata_prefix()` construye un prefijo con toda la estructura descubierta
- **Ejemplo**: *"¿Cuáles son los 10 géneros con mayor ingreso (revenue) promedio?"*

### Fase 3 — Síntesis y Recomendación Final

Combinando los resultados de ambas fases, el sistema genera una **recomendación final** estructurada que incluye: decisión concreta, datos justificativos, riesgos y plan de acción.

---

## 4. Estructura de Archivos — Descripción Detallada

### 4.1. Raíz del proyecto

| Archivo | Descripción |
|---|---|
| run.py | **Punto de entrada** de la aplicación. Carga variables de entorno con `dotenv` y arranca el servidor **Uvicorn** en el puerto 5000 con hot-reload activado. |
| requirements.txt | Dependencias Python: `fastapi`, `uvicorn`, `httpx` (cliente HTTP async), `jinja2` (templates), `python-dotenv`, `pydantic` (validación). |
| README.md | Documentación del proyecto con instrucciones de instalación y arquitectura. |
| LICENSE | Licencia MIT. |

### 4.2. Directorio app — Backend

#### __init__.py
Archivo vacío con cabecera de copyright. Marca el directorio como paquete Python.

#### main.py — API FastAPI (267 líneas)
Es el **controlador principal** de la aplicación. Define:

- **Modelos Pydantic** para validación de entrada:
  - `DecisionRequest`: escenario, pregunta custom, parámetros, vista de datos
  - `FreeQuestionRequest`: para preguntas libres a cualquier endpoint
  - `EmailRequest`: para el envío de correo con la recomendación

- **Endpoints REST**:
  | Ruta | Método | Función |
  |---|---|---|
  | `/` | GET | Sirve la página HTML principal renderizada con Jinja2 |
  | `/api/health` | GET | Verifica conexión con el AI SDK |
  | `/api/scenarios` | GET | Lista los escenarios disponibles |
  | `/api/scenarios/{key}` | GET | Detalle de un escenario (preguntas, parámetros) |
  | `/api/sync-metadata` | POST | Sincroniza metadatos del Data Marketplace al vector store |
  | `/api/decide` | POST | Ejecuta el pipeline completo (respuesta JSON) |
  | `/api/decide-stream` | POST | Pipeline con **streaming SSE** (eventos de progreso en tiempo real) |
  | `/api/discover-views` | GET | Descubre dinámicamente las vistas disponibles |
  | `/api/ask` | POST | Preguntas libres a metadata o data |
  | `/api/send-email` | POST | Envía la recomendación por SMTP |

- Monta archivos estáticos (`/static`) y templates Jinja2 (`/templates`).

#### denodo_client.py — Cliente del AI SDK (154 líneas)
Es el **wrapper de comunicación HTTP** con los endpoints del Denodo AI SDK. Responsabilidades:

- **Autenticación**: HTTP Basic Auth con credenciales de .env
- **Timeout**: 180 segundos para consultas, 300 segundos para sincronización de metadatos
- **Custom Instructions**: Inyecta instrucciones al LLM para que responda en español, no incluya disclaimers, no pida clarificaciones y ejecute consultas directamente
- **`_strip_disclaimer()`**: Post-procesamiento que elimina disclaimers/notas del final de las respuestas del SDK buscando marcadores como `**Disclaimer`, `**Nota:`, `Please note`, etc.
- **Funciones principales**:
  - `answer_metadata_question()` $\rightarrow$ Fase 1 (descubrir estructura)
  - `answer_data_question()` $\rightarrow$ Fase 2 (ejecutar consultas reales)
  - `get_metadata()` $\rightarrow$ Cargar metadatos al vector store
  - `check_health()` $\rightarrow$ Verificar disponibilidad del SDK

#### decision_engine.py — Motor de Decisiones (609 líneas)
Es el **cerebro analítico** del sistema. Contiene:

- **Catálogo `SCENARIOS`**: Diccionario con 7 escenarios predefinidos, cada uno con:
  - `title`, `description`
  - `metadata_questions` (preguntas de Fase 1)
  - `data_questions_template` (plantillas de Fase 2, con placeholders como `{genre}`)
  - `parameters` (configuración de la UI: selects, ranges, text inputs)
  
  Los escenarios son:
  | Clave | Escenario | Vista fija |
  |---|---|---|
  | `production` | ¿Qué película producir? | `admin.movies` |
  | `series_production` | ¿Qué serie producir? | `admin.netflix` |
  | `investment` | ¿En qué contenido invertir? | dinámica (movies/netflix) |
  | `distribution` | ¿En qué mercado distribuir? | dinámica (movies/netflix) |
  | `actor_recommendation` | ¿Qué actor contratar? | `admin.actores` |
  | `statistics` | Estadísticas del catálogo | dinámica |
  | `custom` | Decisión personalizada | la elige el usuario |

- **`STATISTICS_QUERIES`**: Configuración especial para el escenario de estadísticas con queries por categoría (Géneros, Películas, Series, Actores) y configuración de gráficos (`chart_config`).

- **`SCENARIO_VIEWS`**: Mapping de vista fija por escenario para evitar ambigüedad en las consultas.

- **`compute_total_steps()`**: Pre-calcula las preguntas de cada fase y el total de pasos para la barra de progreso. Maneja lógica especial para:
  - Escenarios `investment`/`distribution` con películas vs. series
  - Escenario `statistics` con queries dinámicas por categoría
  - Escenario `custom` con generación automática de preguntas
  - Sustitución de placeholders (`{genre}`, etc.) con parámetros del usuario

- **`_build_metadata_prefix()`**: Construye el contexto de la Fase 1 que se inyecta como prefijo en cada pregunta de la Fase 2. Si hay una vista específica, añade restricciones estrictas (`NO hagas JOIN`, `Solo usa columnas de...`).

- **`build_param_context()`**: Convierte los parámetros del usuario (género, presupuesto, año, rating, idioma...) en texto natural para filtros.

- **`run_decision_pipeline_stream()`**: El **generador asíncrono principal**. Ejecuta:
  1. Resuelve la vista fija del escenario
  2. Ejecuta $N$ preguntas de Fase 1, emitiendo eventos `progress`
  3. Construye contexto de metadatos
  4. Ejecuta $M$ preguntas de Fase 2 con contexto inyectado, emitiendo eventos `progress`
  5. Genera la recomendación final, emitiendo evento `complete`

- **`run_decision_pipeline()`**: Wrapper síncrono que consume el stream y devuelve solo el resultado final.

### 4.3. Directorio static — Frontend

#### style.css (1844 líneas)
Hoja de estilos completa con:
- **Sistema de temas**: Light (azul `#2563eb`) y Dark (rojo `#ff3860`) con CSS custom properties
- **Diseño glassmorphism**: `backdrop-filter: blur()`, superficies semitransparentes
- **Componentes**: tarjetas de escenario con hover animado, barra de progreso por fases, decision card con gradiente, modales para email/PDF, formularios parametrizados
- **Responsive**: adaptado a diferentes tamaños de pantalla
- **Minijuegos**: estilos para Pong (DOM-based) y Pac-Man (canvas)

#### app.js (1026 líneas)
Lógica principal del frontend. Estructura modular:

- **Inicialización** (`DOMContentLoaded`): health check, auto-sync de metadatos, discover views, event listeners
- **Selector de vistas**: modo automático (`🤖 Auto`) o manual con datalist autocompletable
- **Navegación**: SPA-like con secciones ocultas/visibles (`hideAllSections()`, `showScenarios()`, `showResults()`)
- **Preview de escenarios**: Fetch de `/api/scenarios/{key}`, renderizado dinámico de parámetros (select, range, text)
- **Pipeline de decisión** (`runDecision()`):
  - Envía `POST /api/decide-stream`
  - Lee el stream SSE con `ReadableStream` 
  - Actualiza indicadores de fase en tiempo real (metadata $\rightarrow$ data $\rightarrow$ decision)
  - Soporta cancelación con `AbortController`
- **Renderizado de resultados** (`renderResults()`):
  - Decisión final con **Markdown** (biblioteca `marked.js`)
  - Gráficos interactivos con **Chart.js** para el escenario de estadísticas
  - Bloques Q&A colapsables para detalle de cada fase
- **Exportación**:
  - **PDF**: Genera un documento estilizado con `html2pdf.js`, con opción de incluir detalles de metadatos/datos
  - **Email**: Modal que envía la recomendación vía SMTP
- **Charts** (`renderCharts()`): Parsea respuestas con formato `label | valor` y genera gráficos bar/horizontalBar/doughnut con paleta de 15 colores

#### inline-games.js (634 líneas)
**Minijuegos integrados** que se muestran durante la pantalla de carga (mientras el pipeline ejecuta las consultas al AI SDK):

- **Pong**: Implementado con DOM manipulation. El spinner de carga se convierte en la pelota. Dos jugadores (W/S y flechas).
- **Pac-Man**: Implementado con Canvas. Laberinto de 20×17 tiles con dots, power-ups y 4 fantasmas con IA (scatter/chase/frightened).
- Menú flotante con botones para elegir juego y botón de salida.

### 4.4. Directorio templates

#### index.html
Plantilla Jinja2 que define la estructura HTML completa:

- **Header**: Logo, título, badge de health check, selector de vista de datos
- **Scenario section**: Grid de 6 tarjetas de escenario + enlace a decisión personalizada
- **Preview section**: Detalle del escenario con parámetros dinámicos y botón de ejecución
- **Custom section**: Formulario libre (pregunta + preguntas metadata/data opcionales)
- **Results section**: Pantalla de carga con fases + minijuegos, resultados con gráficos, decisión, detalles colapsables, errores, acciones (PDF/email)
- **Modales**: Email y PDF
- **CDNs**: `marked.js` (Markdown), `Chart.js` (gráficos), `html2pdf.js` (exportación PDF)
- Estructura DOM para los minijuegos (Pong field, Pac-Man canvas)

### 4.5. Directorio tests — Suite de Tests

#### test_api.py (184 líneas)
Tests de integración para los endpoints FastAPI usando `httpx.AsyncClient` con `ASGITransport`:
- Tests GET: home, health (connected/disconnected), scenarios, scenario detail
- Tests `/api/decide`: verifica que llama al pipeline correctamente
- Tests `/api/discover-views`: mock de `answer_metadata_question`
- Tests `/api/ask`: preguntas libres a metadata y data
- Tests `/api/sync-metadata`

#### test_decision_engine.py (326 líneas)
Tests unitarios del motor de decisiones:
- `_build_metadata_prefix()`: con/sin contexto, con restricción de vistas
- `build_param_context()`: todos los tipos de parámetros
- `compute_total_steps()`: para cada escenario (production, investment, series, statistics, custom)
- `run_decision_pipeline_stream()`: verifica eventos de progreso y estructura del resultado final
- `run_decision_pipeline()`: verifica el wrapper síncrono

#### test_denodo_client.py (216 líneas)
Tests unitarios del cliente HTTP del AI SDK:
- `_strip_disclaimer()`: todos los patrones de disclaimer
- `_parse_error()`: JSON con detail, dict, texto plano, código HTTP
- `answer_metadata_question()`: mock de respuesta exitosa, con `use_views`, error HTTP
- `answer_data_question()`: respuestas válidas y errores
- `get_metadata()`: sincronización, respuesta 204 No Content, errores
- `check_health()`: conectado, desconectado, timeout

### 4.6. Directorio `casos de uso/`
Contiene capturas de pantalla (1.png - 12.png) y un vídeo de demostración (`Caso de uso - Denodo Flick.mp4`) que documentan el funcionamiento de la aplicación.

---

## 5. Flujo de Datos Completo

$$
\boxed{\text{Usuario selecciona escenario}} \rightarrow \boxed{\text{Configura parámetros}} \rightarrow \boxed{\text{Ejecutar análisis}}
$$

$$
\downarrow
$$

$$
\boxed{\text{Frontend envía POST /api/decide-stream}} \xrightarrow{\text{SSE}} \boxed{\text{Backend orquesta 3 fases}}
$$

$$
\downarrow
$$

$$
\boxed{\text{Fase 1: } N \text{ preguntas metadata}} \rightarrow \boxed{\text{Contexto inyectado}} \rightarrow \boxed{\text{Fase 2: } M \text{ preguntas data}} \rightarrow \boxed{\text{Fase 3: Recomendación}}
$$

$$
\downarrow
$$

$$
\boxed{\text{Resultados renderizados: Markdown + Charts + Detalles}} \rightarrow \boxed{\text{Exportar PDF / Email}}
$$

---

## 6. Tecnologías Utilizadas

| Capa | Tecnología | Propósito |
|---|---|---|
| Backend | **FastAPI** + **Uvicorn** | API REST asíncrona con hot-reload |
| HTTP Client | **httpx** (async) | Comunicación con Denodo AI SDK |
| Validación | **Pydantic** | Modelos de entrada tipados |
| Templates | **Jinja2** | Renderizado HTML server-side |
| Frontend | **Vanilla JS** | Lógica SPA sin frameworks |
| Markdown | **marked.js** | Renderizado de respuestas del LLM |
| Gráficos | **Chart.js** | Visualización de estadísticas |
| PDF | **html2pdf.js** | Exportación de recomendaciones |
| Datos | **Denodo AI SDK** (RAG) | Acceso a datos virtualizados vía LLM |
| Tests | **pytest** + **pytest-asyncio** | Tests unitarios y de integración |

---

## 7. Conceptos Clave del Diseño

1. **Inyección de contexto entre fases**: Los resultados de la Fase 1 se prependen como prefijo textual en cada pregunta de la Fase 2, garantizando que las consultas VQL se basen en la estructura real descubierta.

2. **Restricción de vistas**: Los escenarios predefinidos fuerzan una vista fija (`admin.movies`, `admin.netflix`, `admin.actores`) para evitar que el LLM se confunda con múltiples tablas similares.

3. **Streaming SSE**: El pipeline emite eventos de progreso en tiempo real, permitiendo mostrar en qué fase/paso se encuentra sin esperar a que termine todo el análisis.

4. **Parametrización dinámica**: Los parámetros del usuario (género, presupuesto, año, rating...) se inyectan tanto en las preguntas como en las instrucciones del LLM mediante placeholders y `build_param_context()`.

5. **Limpieza de disclaimers**: El cliente HTTP post-procesa todas las respuestas del AI SDK para eliminar advertencias y notas que el LLM suele añadir al final.

6. **Custom Instructions**: Se envían instrucciones personalizadas al LLM en cada llamada para forzar respuesta en español, ejecución directa sin clarificaciones, y uso exclusivo de la vista especificada.