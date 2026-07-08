"""ChromaDB vector store access — encapsulated behind a thin repository."""

from __future__ import annotations

import re
from functools import lru_cache
from typing import List

from langchain_chroma import Chroma  # type: ignore[import-untyped]
from langchain_core.documents import Document
from langchain_core.vectorstores import VectorStoreRetriever

from ..core.config import get_settings
from ..core.llm_factory import get_embeddings
from ..core.logging import get_logger

logger = get_logger(__name__)


def _slugify(value: str, max_length: int = 32) -> str:
    """Reduce a model tag like ``gemma:2b`` to a Chroma-safe identifier
    (alphanumerics + underscore, lowercased, length-capped). Used to build
    collection names that auto-segregate vectors by embedding model."""
    cleaned = re.sub(r"[^A-Za-z0-9]+", "_", value or "").strip("_").lower()
    return (cleaned or "default")[:max_length]


class VectorRepository:
    """Read/write access to the Chroma collection."""

    def __init__(self) -> None:
        settings = get_settings()
        # Namespace the physical collection by (provider, embed_model) so the
        # vectors never clash on dimension when you switch models. Chroma
        # locks a collection to its first embedding's dimensionality; with
        # this scheme the next switch just creates a sibling collection.
        provider = settings.embed_provider or settings.resolve_provider()
        if provider == "ollama":
            embed_id = settings.effective_ollama_embed_model
        elif provider == "gemini":
            embed_id = settings.gemini_embed_model
        elif provider == "openai":
            embed_id = settings.openai_embed_model
        elif provider == "huggingface":
            embed_id = settings.local_embed_model
        else:
            embed_id = settings.local_embed_model
        self._collection = (
            f"{settings.chroma_collection}__{provider}__{_slugify(embed_id)}"
        )
        self._persist_dir = settings.chroma_persist_dir
        self._top_k = settings.retriever_top_k
        self._store = Chroma(
            collection_name=self._collection,
            embedding_function=get_embeddings(),
            persist_directory=self._persist_dir,
        )
        logger.info(
            "VECTOR_REPO | collection=%s | provider=%s | embed=%s",
            self._collection,
            provider,
            embed_id,
        )

    # -- queries ----------------------------------------------------------
    def as_retriever(self) -> VectorStoreRetriever:
        return self._store.as_retriever(
            search_type="mmr",
            search_kwargs={
                "k": self._top_k,
                "fetch_k": self._top_k * 3,
                "lambda_mult": 0.7,
            },
        )

    def similarity_search(self, query: str, k: int | None = None) -> List[Document]:
        return self._store.similarity_search(query, k=k or self._top_k)

    def list_documents(self) -> List[dict]:
        """Return one entry per distinct source document in the collection.

        Aggregates the chunk count per source so the Library UI can display
        the corpus without ever holding the full chunk content in memory.
        """
        try:
            raw = self._store._collection.get(include=["metadatas"])
        except Exception as exc:  # noqa: BLE001
            logger.warning("VECTOR_REPO | list_documents failed: %s", exc)
            return []

        bucket: dict[str, dict] = {}
        for meta in raw.get("metadatas") or []:
            if not isinstance(meta, dict):
                continue
            source = meta.get("source") or meta.get("title") or "unknown"
            entry = bucket.setdefault(
                source,
                {
                    "id": source,
                    "title": meta.get("title") or source,
                    "source": source,
                    "year": meta.get("year"),
                    "chunks": 0,
                },
            )
            entry["chunks"] += 1
        return sorted(bucket.values(), key=lambda d: d["title"].lower())

    # -- writes -----------------------------------------------------------
    def add_documents(self, docs: List[Document]) -> int:
        if not docs:
            return 0
        self._store.add_documents(docs)
        try:
            # Older Chroma versions; new versions auto-persist
            self._store.persist()  # type: ignore[attr-defined]
        except Exception:  # noqa: BLE001
            pass
        logger.info("VECTOR_REPO | added %d chunk(s)", len(docs))
        return len(docs)

    @property
    def collection(self) -> str:
        return self._collection

    @property
    def persist_dir(self) -> str:
        return self._persist_dir


@lru_cache(maxsize=1)
def get_vector_repository() -> VectorRepository:
    return VectorRepository()
