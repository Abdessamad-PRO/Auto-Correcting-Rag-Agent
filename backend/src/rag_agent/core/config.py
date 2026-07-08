"""Centralised application configuration.

Resolves the active LLM provider from environment variables in a deterministic
priority order: explicit ``LLM_PROVIDER`` override → Gemini → OpenAI → Grok.
"""

from __future__ import annotations

from functools import lru_cache
from typing import List, Literal, Optional

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ProviderName = Literal["gemini", "openai", "grok", "ollama"]
EmbeddingProviderName = Literal["gemini", "openai", "ollama", "huggingface"]


class Settings(BaseSettings):
    """Application settings loaded from environment / .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- Provider override (optional) -------------------------------------
    llm_provider: Optional[ProviderName] = None
    #: When true, force Ollama as the primary provider regardless of which
    #: remote API keys are present. Remote providers (if their keys are set)
    #: still appear later in the fallback chain.
    local: bool = False

    # --- Embeddings provider override (optional) --------------------------
    embed_provider: Optional[EmbeddingProviderName] = Field(
        default=None,
        validation_alias=AliasChoices("EMBED_PROVIDER", "EMBEDDINGS_PROVIDER"),
    )

    # --- Provider credentials --------------------------------------------
    gemini_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    grok_api_key: Optional[str] = None

    # --- Models -----------------------------------------------------------
    gemini_model: str = "gemini-flash-latest"
    gemini_embed_model: str = "models/gemini-embedding-001"
    #: Same-provider fallback used when ``gemini_model`` is rate-limited or fails.
    gemini_fallback_model: str = "gemini-pro-latest"

    openai_model: str = "gpt-4o"
    openai_embed_model: str = "text-embedding-3-small"

    grok_model: str = "grok-4-fast-reasoning"
    local_embed_model: str = "sentence-transformers/all-MiniLM-L6-v2"

    # --- Ollama (local fallback / local-first) --------------------------
    #: URL of the local Ollama daemon (default Windows install: 11434).
    ollama_base_url: str = "http://localhost:11434"
    #: Primary Ollama model — used when ``local=True`` or when the resolver
    #: falls back to ollama for any other reason.
    ollama_model: str = "deepseek-r1:1.5b"
    #: Comma-separated list of ``ollama list``-pulled model tags, tried as
    #: extra fallbacks AFTER the primary chat model has failed.
    ollama_fallback_models_raw: str = "gemma:2b"
    #: Ollama model used for embeddings. Empty → reuse ``ollama_model``.
    #: For best retrieval quality pull a dedicated embedding model:
    #:     ollama pull nomic-embed-text
    #: …then set OLLAMA_EMBED_MODEL=nomic-embed-text in .env.
    ollama_embed_model: str = ""

    llm_temperature: float = 0.0

    # --- Vector store -----------------------------------------------------
    chroma_persist_dir: str = "./chroma_db"
    chroma_collection: str = "gcn_eeg_papers"
    retriever_top_k: int = 5

    # --- Agent behaviour --------------------------------------------------
    max_retrieve_iterations: int = 3
    relevance_threshold: float = 0.5

    # --- Web search -------------------------------------------------------
    web_search_provider: Literal["duckduckgo", "tavily"] = "duckduckgo"
    tavily_api_key: Optional[str] = None
    web_search_max_results: int = 5

    # --- API server -------------------------------------------------------
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    #: Comma-separated string in the env; use ``cors_origins`` for the parsed list.
    #: Kept as a plain ``str`` so pydantic-settings does not attempt to JSON-decode it.
    cors_origins_raw: str = Field(
        default="http://localhost:4200,http://127.0.0.1:4200",
        validation_alias=AliasChoices("CORS_ORIGINS", "CORS_ORIGINS_RAW"),
    )
    log_level: str = "INFO"

    @property
    def cors_origins(self) -> List[str]:
        return [o.strip() for o in self.cors_origins_raw.split(",") if o.strip()]

    @property
    def ollama_fallback_models(self) -> List[str]:
        return [m.strip() for m in self.ollama_fallback_models_raw.split(",") if m.strip()]

    @property
    def effective_ollama_embed_model(self) -> str:
        """Embed model used by Ollama. Falls back to the chat model when the
        dedicated embed model env var is empty so a fresh setup works without
        needing an extra ``ollama pull``."""
        return self.ollama_embed_model.strip() or self.ollama_model

    # ---------------------------------------------------------------------
    # Derived
    # ---------------------------------------------------------------------
    def resolve_provider(self) -> ProviderName:
        """Return the active LLM provider.

        Priority:
            1. ``LOCAL=true``                      → ollama (no key required).
            2. Explicit ``LLM_PROVIDER`` env var   → that provider.
            3. First provider with a non-empty API key in the order
               Gemini → OpenAI → Grok → ollama (last resort).
        """
        if self.local:
            return "ollama"

        if self.llm_provider:
            if self.llm_provider == "ollama":
                return "ollama"
            key = self._provider_key(self.llm_provider)
            if not key:
                raise RuntimeError(
                    f"LLM_PROVIDER={self.llm_provider!r} but no API key set for it."
                )
            return self.llm_provider

        if self.gemini_api_key:
            return "gemini"
        if self.openai_api_key:
            return "openai"
        if self.grok_api_key:
            return "grok"

        # No remote keys configured — assume the user wants pure local mode.
        return "ollama"

    def _provider_key(self, provider: ProviderName) -> Optional[str]:
        return {
            "gemini": self.gemini_api_key,
            "openai": self.openai_api_key,
            "grok": self.grok_api_key,
            "ollama": "local",  # placeholder, no key required
        }[provider]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached settings accessor."""
    return Settings()
