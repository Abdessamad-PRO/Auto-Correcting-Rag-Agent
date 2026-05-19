"""Provider-agnostic LLM & embedding factories.

Selects Gemini, OpenAI, or Grok at runtime based on which API key is present.
All factories are memoised so a single chat model / embedding model is shared
across the whole process.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from langchain_core.embeddings import Embeddings
from langchain_core.language_models.chat_models import BaseChatModel

from .config import ProviderName, get_settings
from .logging import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Chat model factory
# ---------------------------------------------------------------------------


@lru_cache(maxsize=1)
def get_chat_model() -> BaseChatModel:
    settings = get_settings()
    provider = settings.resolve_provider()
    logger.info("LLM_FACTORY | provider=%s", provider)

    if provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(
            model=settings.gemini_model,
            google_api_key=settings.gemini_api_key,
            temperature=settings.llm_temperature,
        )

    if provider == "openai":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=settings.openai_model,
            api_key=settings.openai_api_key,
            temperature=settings.llm_temperature,
        )

    if provider == "grok":
        from langchain_xai import ChatXAI

        return ChatXAI(
            model=settings.grok_model,
            api_key=settings.grok_api_key,
            temperature=settings.llm_temperature,
        )

    raise RuntimeError(f"Unsupported provider: {provider}")


def get_structured_chat_model(schema: Any) -> Any:
    """Return a chat model bound to a structured Pydantic output schema."""
    return get_chat_model().with_structured_output(schema)


# ---------------------------------------------------------------------------
# Embedding factory
# ---------------------------------------------------------------------------


@lru_cache(maxsize=1)
def get_embeddings() -> Embeddings:
    settings = get_settings()
    provider: ProviderName = settings.resolve_provider()
    logger.info("EMBED_FACTORY | provider=%s", provider)

    if provider == "gemini":
        from langchain_google_genai import GoogleGenerativeAIEmbeddings

        return GoogleGenerativeAIEmbeddings(
            model=settings.gemini_embed_model,
            google_api_key=settings.gemini_api_key,
        )

    if provider == "openai":
        from langchain_openai import OpenAIEmbeddings

        return OpenAIEmbeddings(
            model=settings.openai_embed_model,
            api_key=settings.openai_api_key,
        )

    # Grok has no embeddings API — fall back to a local HuggingFace model
    if provider == "grok":
        from langchain_huggingface import HuggingFaceEmbeddings

        logger.warning(
            "EMBED_FACTORY | grok has no embedding API — using local model '%s'",
            settings.local_embed_model,
        )
        return HuggingFaceEmbeddings(model_name=settings.local_embed_model)

    raise RuntimeError(f"Unsupported provider: {provider}")
