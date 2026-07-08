"""Provider-agnostic LLM & embedding factories — with auto-fallback.

The active provider (Gemini / OpenAI / Grok) is selected from the API keys
present in ``.env``. To stay responsive when remote quotas are exhausted, the
chat factory composes a **resilient runnable** that tries multiple models in
order via LangChain's ``Runnable.with_fallbacks`` mechanism:

    primary remote model
        → same-provider fallback (e.g. Gemini flash → Gemini pro)
        → local Ollama models (e.g. gemma → deepseek-r1)

Every call site in the codebase goes through :func:`get_chat_model` or
:func:`get_structured_chat_model`, so nodes / chains automatically inherit
the entire fallback chain without any per-node changes.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Any, List

from langchain_core.embeddings import Embeddings
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.runnables import Runnable

from .config import ProviderName, get_settings
from .logging import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Patch: disable google-genai's internal tenacity retry loop
# ---------------------------------------------------------------------------
#
# Without this patch, every 429 from Gemini triggers the SDK's built-in
# 1s→2s→4s→8s→16s→32s exponential backoff *before* any exception reaches
# us — so our `Runnable.with_fallbacks([...])` chain idles for ~60 s before
# moving on to Gemini Pro / Ollama. With the patch, the 429 surfaces in one
# round-trip and the fallback chain advances within milliseconds.

def _disable_genai_internal_retry() -> None:
    try:
        from google.genai import _api_client as _gc  # type: ignore[import-not-found]

        def _request_no_retry(self, http_request, http_options=None, stream=False):
            return self._request_once(http_request, stream)

        _gc.BaseApiClient._request = _request_no_retry  # type: ignore[method-assign]
        logger.info("LLM_FACTORY | patched google-genai: internal retry disabled")
    except Exception as exc:  # noqa: BLE001
        logger.warning("LLM_FACTORY | could not patch google-genai retry: %s", exc)


_disable_genai_internal_retry()


# ---------------------------------------------------------------------------
# Spec
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _ChatSpec:
    """A single (provider, model) pair in the fallback chain."""

    provider: str       # gemini | openai | grok | ollama
    model: str

    @property
    def label(self) -> str:
        return f"{self.provider}:{self.model}"


# ---------------------------------------------------------------------------
# Build one concrete chat model
# ---------------------------------------------------------------------------


def _build_chat(spec: _ChatSpec) -> BaseChatModel:
    """Instantiate the concrete LangChain chat model for the given spec."""
    s = get_settings()

    if spec.provider == "gemini":
        if not s.gemini_api_key:
            raise RuntimeError("Gemini selected but GEMINI_API_KEY is not set.")
        from langchain_google_genai import ChatGoogleGenerativeAI

        # `max_retries=0` disables the Google SDK's internal exponential
        # backoff on 429/5xx. Without this the SDK keeps retrying for
        # minutes and our `with_fallbacks` chain never gets a chance to
        # move on to Gemini Pro / Ollama.
        return ChatGoogleGenerativeAI(
            model=spec.model,
            google_api_key=s.gemini_api_key,
            temperature=s.llm_temperature,
            max_retries=0,
        )

    if spec.provider == "openai":
        if not s.openai_api_key:
            raise RuntimeError("OpenAI selected but OPENAI_API_KEY is not set.")
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=spec.model,
            api_key=s.openai_api_key,
            temperature=s.llm_temperature,
            max_retries=0,
        )

    if spec.provider == "grok":
        if not s.grok_api_key:
            raise RuntimeError("Grok selected but GROK_API_KEY is not set.")
        from langchain_xai import ChatXAI

        return ChatXAI(
            model=spec.model,
            api_key=s.grok_api_key,
            temperature=s.llm_temperature,
            max_retries=0,
        )

    if spec.provider == "ollama":
        # Local Ollama daemon. Construction is cheap (no network call) — any
        # error from `ollama serve` being down is raised at invoke time and
        # naturally caught by the next fallback in the chain.
        from langchain_ollama import ChatOllama

        return ChatOllama(
            model=spec.model,
            base_url=s.ollama_base_url,
            temperature=s.llm_temperature,
        )

    raise RuntimeError(f"Unknown provider in fallback chain: {spec.provider}")


# ---------------------------------------------------------------------------
# Build the ordered fallback chain
# ---------------------------------------------------------------------------


def _resilient_chain() -> List[_ChatSpec]:
    """Compose the ordered preference list.

    Primary = whichever remote provider has an API key set (Gemini > OpenAI > Grok).
    Same-provider fallback comes next (Gemini flash → Gemini pro).
    Local Ollama models close the chain so the agent keeps working even if all
    remote APIs are rate-limited or unreachable.
    """
    s = get_settings()
    primary: ProviderName = s.resolve_provider()
    chain: List[_ChatSpec] = []
    seen: set[tuple[str, str]] = set()

    def _add(provider: str, model: str) -> None:
        key = (provider, model)
        if model and key not in seen:
            seen.add(key)
            chain.append(_ChatSpec(provider, model))

    # ── Primary ─────────────────────────────────────────────────────────
    if primary == "gemini":
        _add("gemini", s.gemini_model)
        _add("gemini", s.gemini_fallback_model)
    elif primary == "openai":
        _add("openai", s.openai_model)
    elif primary == "grok":
        _add("grok", s.grok_model)
    elif primary == "ollama":
        _add("ollama", s.ollama_model)

    # ── Remote fallbacks (only when local-first is enabled) ────────────
    # If the user explicitly set LOCAL=true, the local Ollama is primary —
    # but if remote keys are also set we still want them as overflow.
    if primary == "ollama":
        if s.gemini_api_key:
            _add("gemini", s.gemini_model)
            _add("gemini", s.gemini_fallback_model)
        if s.openai_api_key:
            _add("openai", s.openai_model)
        if s.grok_api_key:
            _add("grok", s.grok_model)

    # ── Local Ollama fallbacks (always last) ───────────────────────────
    # Include OLLAMA_MODEL too (it's the user's preferred local model) so
    # remote-primary chains still benefit from it. The de-dup in `_add`
    # makes this safe even when Ollama is already the primary.
    _add("ollama", s.ollama_model)
    for model in s.ollama_fallback_models:
        _add("ollama", model)

    return chain


def _build_runnables(specs: List[_ChatSpec]) -> List[BaseChatModel]:
    """Instantiate each spec, skipping ones that fail to construct."""
    runnables: List[BaseChatModel] = []
    for spec in specs:
        try:
            runnables.append(_build_chat(spec))
        except Exception as exc:  # noqa: BLE001
            logger.warning("LLM_FACTORY | skip fallback %s: %s", spec.label, exc)
    return runnables


# ---------------------------------------------------------------------------
# Public API — chat models with auto-fallback
# ---------------------------------------------------------------------------


@lru_cache(maxsize=1)
def get_chat_model() -> Runnable:
    """Return a Runnable that wraps the primary model with a fallback chain."""
    specs = _resilient_chain()
    logger.info(
        "LLM_FACTORY | chat fallback chain: %s",
        "  →  ".join(s.label for s in specs),
    )
    runnables = _build_runnables(specs)
    if not runnables:
        raise RuntimeError("No chat model could be built. Check API keys / Ollama.")
    if len(runnables) == 1:
        return runnables[0]
    return runnables[0].with_fallbacks(runnables[1:])


def get_structured_chat_model(schema: Any) -> Runnable:
    """Same as :func:`get_chat_model` but with structured output bound to *every*
    link in the fallback chain. Each provider gets its own
    ``.with_structured_output(schema)`` binding so fallbacks remain typed.
    """
    specs = _resilient_chain()
    bound: List[Runnable] = []
    for spec in specs:
        try:
            bound.append(_build_chat(spec).with_structured_output(schema))
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "LLM_FACTORY | skip structured fallback %s: %s", spec.label, exc
            )
    if not bound:
        raise RuntimeError("No structured chat model could be built.")
    if len(bound) == 1:
        return bound[0]
    return bound[0].with_fallbacks(bound[1:])


# ---------------------------------------------------------------------------
# Embeddings — no fallback chain (vector dimensions must stay consistent
# within a single Chroma collection; switching embedding model = new collection)
# ---------------------------------------------------------------------------


@lru_cache(maxsize=1)
def get_embeddings() -> Embeddings:
    s = get_settings()
    provider = s.embed_provider or s.resolve_provider()
    logger.info("EMBED_FACTORY | provider=%s", provider)

    if provider == "gemini":
        from langchain_google_genai import GoogleGenerativeAIEmbeddings

        return GoogleGenerativeAIEmbeddings(
            model=s.gemini_embed_model,
            google_api_key=s.gemini_api_key,
        )

    if provider == "openai":
        from langchain_openai import OpenAIEmbeddings

        return OpenAIEmbeddings(
            model=s.openai_embed_model,
            api_key=s.openai_api_key,
        )

    if provider == "ollama":
        # Use Ollama's own /api/embeddings — keeps everything offline. If
        # OLLAMA_EMBED_MODEL is unset we reuse OLLAMA_MODEL so a fresh setup
        # works without an extra `ollama pull nomic-embed-text`.
        from langchain_ollama import OllamaEmbeddings

        embed_model = s.effective_ollama_embed_model
        logger.info("EMBED_FACTORY | ollama embedding model: %s", embed_model)
        return OllamaEmbeddings(model=embed_model, base_url=s.ollama_base_url)

    if provider == "huggingface":
        from langchain_huggingface import HuggingFaceEmbeddings

        logger.info("EMBED_FACTORY | using local HF model '%s'", s.local_embed_model)
        return HuggingFaceEmbeddings(model_name=s.local_embed_model)

    # Grok ships no embedding API. Fall back to a local HuggingFace model.
    # First load needs internet (or a pre-warmed HF cache); subsequent runs
    # serve from `~/.cache/huggingface`.
    if provider == "grok":
        from langchain_huggingface import HuggingFaceEmbeddings

        logger.warning(
            "EMBED_FACTORY | grok has no embedding API — using local HF model '%s'",
            s.local_embed_model,
        )
        return HuggingFaceEmbeddings(model_name=s.local_embed_model)

    raise RuntimeError(f"Unsupported provider: {provider}")
