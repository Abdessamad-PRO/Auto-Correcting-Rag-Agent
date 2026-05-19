"""FastAPI application entry point.

Wires controllers, CORS, logging, and exposes a ``run()`` console script
(``uv run rag-api``) that launches uvicorn.
"""

from __future__ import annotations

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .controllers.agent_controller import router as agent_router
from .controllers.evaluation_controller import router as evaluation_router
from .controllers.health_controller import router as health_router
from .controllers.ingestion_controller import router as ingestion_router
from .core.config import get_settings
from .core.logging import configure_logging


def create_app() -> FastAPI:
    configure_logging()
    settings = get_settings()

    app = FastAPI(
        title="Auto-Correcting RAG Agent API",
        version="0.2.0",
        description=(
            "Backend for the ENSET research agent. Multi-provider LLM "
            "(Gemini / OpenAI / Grok), self-correcting RAG with web-search "
            "fallback, human-in-the-loop, and prompt A/B evaluation."
        ),
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health_router)
    app.include_router(agent_router)
    app.include_router(ingestion_router)
    app.include_router(evaluation_router)

    return app


app = create_app()


def run() -> None:
    """Console-script entry point (``uv run rag-api``)."""
    settings = get_settings()
    uvicorn.run(
        "rag_agent.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=False,
    )


if __name__ == "__main__":
    run()
