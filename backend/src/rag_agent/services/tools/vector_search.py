"""Thin facade over the vector repository for use inside agent nodes/tools."""

from __future__ import annotations

from typing import List

from langchain_core.documents import Document

from ...repositories.vector_repository import get_vector_repository


def vector_search(query: str, k: int | None = None) -> List[Document]:
    repo = get_vector_repository()
    docs = repo.similarity_search(query, k=k)
    for d in docs:
        d.metadata.setdefault("origin", "vector")
    return docs
