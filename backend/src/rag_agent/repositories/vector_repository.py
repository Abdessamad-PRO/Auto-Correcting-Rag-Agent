"""ChromaDB vector store access — encapsulated behind a thin repository."""

from __future__ import annotations

from functools import lru_cache
from typing import List

from langchain_chroma import Chroma  # type: ignore[import-untyped]
from langchain_core.documents import Document
from langchain_core.vectorstores import VectorStoreRetriever

from ..core.config import get_settings
from ..core.llm_factory import get_embeddings
from ..core.logging import get_logger

logger = get_logger(__name__)


class VectorRepository:
    """Read/write access to the Chroma collection."""

    def __init__(self) -> None:
        settings = get_settings()
        self._collection = settings.chroma_collection
        self._persist_dir = settings.chroma_persist_dir
        self._top_k = settings.retriever_top_k
        self._store = Chroma(
            collection_name=self._collection,
            embedding_function=get_embeddings(),
            persist_directory=self._persist_dir,
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
