# Copyright (c) 2026 Rafael Casado, Joel Candal, Diego Rodríguez, Santiago Neira
# Licensed under the MIT License. See LICENSE file for details.

"""
Denodo AI SDK Client
Wrapper para comunicarse con los endpoints del Denodo AI SDK:
- /answerMetadataQuestion (Fase de análisis)
- /answerDataQuestion (Fase de ejecución)
- /getMetadata (Carga de metadatos al vector store)

La API usa HTTP Basic Auth para autenticación.
"""

import httpx
import os
from dotenv import load_dotenv

load_dotenv()

DENODO_AI_SDK_URL = os.getenv("DENODO_AI_SDK_URL", "http://localhost:8008")
DENODO_USERNAME = os.getenv("DENODO_USERNAME", "admin")
DENODO_PASSWORD = os.getenv("DENODO_PASSWORD", "admin")

TIMEOUT = httpx.Timeout(180.0, connect=10.0)

CUSTOM_INSTRUCTIONS = "Responde siempre en español. No incluyas disclaimers, advertencias ni notas sobre la precisión de los datos al final de la respuesta. NUNCA pidas clarificaciones ni menciones ambigüedades. Si hay varias métricas posibles (revenue, score, popularidad), usa todas las disponibles en la consulta. Ejecuta la consulta directamente con tu mejor interpretación."

# Patrones de disclaimer que el SDK suele añadir al final
_DISCLAIMER_MARKERS = [
    "**Disclaimer",
    "**Nota:",
    "**Advertencia",
    "*Disclaimer",
    "*Nota:",
    "Disclaimer:",
    "Note:",
    "Please note",
    "Ten en cuenta que",
    "Es importante tener en cuenta",
    "DISCLAIMER",
]


def _strip_disclaimer(text: str) -> str:
    """Elimina disclaimers y notas finales de la respuesta del SDK."""
    if not text:
        return text
    for marker in _DISCLAIMER_MARKERS:
        idx = text.rfind(marker)
        if idx > 0 and idx > len(text) * 0.5:  # Solo si está en la segunda mitad
            text = text[:idx].rstrip()
    return text


def _auth() -> httpx.BasicAuth:
    """Genera la autenticación HTTP Basic para el AI SDK."""
    return httpx.BasicAuth(username=DENODO_USERNAME, password=DENODO_PASSWORD)


def _parse_error(response: httpx.Response) -> str:
    """Extrae mensaje de error legible de la respuesta HTTP."""
    try:
        data = response.json()
        if isinstance(data, dict):
            detail = data.get("detail", data)
            if isinstance(detail, dict):
                return detail.get("error", str(detail))
            return str(detail)
        return str(data)
    except Exception:
        return response.text or f"HTTP {response.status_code}"


async def answer_metadata_question(question: str, use_views: str | None = None) -> dict:
    """
    Fase 1 - Análisis de metadatos.
    Usa /answerMetadataQuestion para descubrir qué datos hay disponibles
    en el Data Marketplace (tablas, columnas, relaciones).
    """
    url = f"{DENODO_AI_SDK_URL}/answerMetadataQuestion"
    payload = {
        "question": question,
        "custom_instructions": CUSTOM_INSTRUCTIONS,
    }
    if use_views:
        payload["use_views"] = use_views

    async with httpx.AsyncClient(timeout=TIMEOUT, verify=False, auth=_auth()) as client:
        response = await client.post(url, json=payload)
        if response.status_code >= 400:
            raise Exception(_parse_error(response))
        data = response.json()
        if isinstance(data, dict) and "answer" in data:
            data["answer"] = _strip_disclaimer(data["answer"])
        return data


async def answer_data_question(question: str, use_views: str | None = None) -> dict:
    """
    Fase 2 - Ejecución de consultas.
    Usa /answerDataQuestion para ejecutar consultas VQL sobre los datos
    de Denodo y obtener resultados concretos.
    """
    url = f"{DENODO_AI_SDK_URL}/answerDataQuestion"
    payload = {
        "question": question,
        "custom_instructions": CUSTOM_INSTRUCTIONS,
    }
    if use_views:
        payload["use_views"] = use_views

    async with httpx.AsyncClient(timeout=TIMEOUT, verify=False, auth=_auth()) as client:
        response = await client.post(url, json=payload)
        if response.status_code >= 400:
            raise Exception(_parse_error(response))
        data = response.json()
        if isinstance(data, dict) and "answer" in data:
            data["answer"] = _strip_disclaimer(data["answer"])
        return data


async def get_metadata(database_names: str = "") -> dict:
    """
    Carga/sincroniza los metadatos del Data Marketplace en el vector store.
    Debe ejecutarse después de sincronizar el Data Marketplace.
    """
    url = f"{DENODO_AI_SDK_URL}/getMetadata"
    params = {}
    if database_names:
        params["vdp_database_names"] = database_names

    async with httpx.AsyncClient(timeout=httpx.Timeout(300.0, connect=10.0), verify=False, auth=_auth()) as client:
        response = await client.get(url, params=params)
        if response.status_code >= 400:
            raise Exception(_parse_error(response))
        # 204 No Content = successful but empty
        if response.status_code == 204:
            return {"status": "synced", "message": "Metadatos sincronizados (sin contenido nuevo)."}
        return response.json()


async def check_health() -> dict:
    """Verifica que el AI SDK esté disponible y devuelve info detallada."""
    url = f"{DENODO_AI_SDK_URL}/health"
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(5.0), verify=False) as client:
            response = await client.get(url)
            return {"status": response.status_code == 200, "data": response.json() if response.status_code == 200 else None}
    except Exception as e:
        return {"status": False, "error": str(e)}
