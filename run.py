# Copyright (c) 2026 Rafael Casado, Joel Candal, Diego Rodríguez, Santiago Neira
# Licensed under the MIT License. See LICENSE file for details.

"""
Denodo Flick — Punto de entrada
Herramienta de toma de decisiones con Denodo AI SDK
HackUDC 2026
"""

import uvicorn
from dotenv import load_dotenv
import os

load_dotenv()

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=os.getenv("APP_HOST", "0.0.0.0"),
        port=int(os.getenv("APP_PORT", 5000)),
        reload=True,
    )
