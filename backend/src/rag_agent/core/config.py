"""Centralised application configuration.

Resolves the active LLM provider from environment variables in a deterministic
priority order: explicit ``LLM_PROVIDER`` override → Gemini → OpenAI → Grok.
"""

from __future__ import annotations

from functools import lru_cache
from typing import List, Literal, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ProviderName = Literal["gemini", "openai", "grok"]


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

    # --- Provider credentials --------------------------------------------
    gemini_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    grok_api_key: Optional[str] = None

    # --- Models -----------------------------------------------------------
    gemini_model: str = "gemini-1.5-pro"
    gemini_embed_model: str = "models/text-embedding-004"

    openai_model: str = "gpt-4o"
    openai_embed_model: str = "text-embedding-3-small"

    grok_model: str = "grok-2-latest"
    local_embed_model: str = "sentence-transformers/all-MiniLM-L6-v2"

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
    cors_origins: List[str] = Field(
        default_factory=lambda: ["http://localhost:4200", "http://127.0.0.1:4200"]
    )
    log_level: str = "INFO"

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_cors(cls, value):
        if isinstance(value, str):
            return [o.strip() for o in value.split(",") if o.strip()]
        return value

    # ---------------------------------------------------------------------
    # Derived
    # ---------------------------------------------------------------------
    def resolve_provider(self) -> ProviderName:
        """Return the active LLM provider.

        Priority:
            1. Explicit ``LLM_PROVIDER`` env var (if its key is present).
            2. First provider with a non-empty API key in the order
               Gemini → OpenAI → Grok.
        """
        if self.llm_provider:
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

        raise RuntimeError(
            "No LLM provider configured. Set one of GEMINI_API_KEY, OPENAI_API_KEY, "
            "or GROK_API_KEY in the .env file."
        )

    def _provider_key(self, provider: ProviderName) -> Optional[str]:
        return {
            "gemini": self.gemini_api_key,
            "openai": self.openai_api_key,
            "grok": self.grok_api_key,
        }[provider]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached settings accessor."""
    return Settings()
