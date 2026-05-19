"""GET /api/health — liveness probe + provider introspection."""

from __future__ import annotations

from fastapi import APIRouter

from ..core.config import get_settings
from ..models.schemas import HealthResponse

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    settings = get_settings()
    provider = settings.resolve_provider()
    model = {
        "gemini": settings.gemini_model,
        "openai": settings.openai_model,
        "grok": settings.grok_model,
    }[provider]
    return HealthResponse(
        status="ok",
        provider=provider,
        model=model,
        chroma_collection=settings.chroma_collection,
        chroma_persist_dir=settings.chroma_persist_dir,
        web_search_provider=settings.web_search_provider,
    )
