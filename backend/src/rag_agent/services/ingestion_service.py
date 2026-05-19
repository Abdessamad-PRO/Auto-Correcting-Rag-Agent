"""Corpus ingestion service — PDF folder or uploaded files → ChromaDB."""

from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path
from typing import Iterable, List

from fastapi import UploadFile

from ..core.logging import get_logger
from ..models.schemas import IngestResponse
from ..repositories.document_repository import DocumentRepository
from ..repositories.vector_repository import get_vector_repository

logger = get_logger(__name__)


class IngestionService:
    def __init__(self) -> None:
        self._doc_repo = DocumentRepository()
        self._vec_repo = get_vector_repository()

    def ingest_directory(self, pdf_dir: str) -> IngestResponse:
        chunks = self._doc_repo.load_pdf_directory(pdf_dir)
        # Count PDF files for the response
        n_files = len({c.metadata.get("source") for c in chunks if c.metadata.get("source")})
        added = self._vec_repo.add_documents(chunks)
        return IngestResponse(
            files_ingested=n_files,
            chunks_added=added,
            collection=self._vec_repo.collection,
            persist_dir=self._vec_repo.persist_dir,
        )

    async def ingest_uploads(self, files: Iterable[UploadFile]) -> IngestResponse:
        """Persist uploaded PDFs to a temp folder, then run directory ingestion."""
        with tempfile.TemporaryDirectory(prefix="rag_upload_") as tmp:
            tmp_path = Path(tmp)
            saved_files: List[Path] = []
            for f in files:
                if not f.filename:
                    continue
                dest = tmp_path / Path(f.filename).name
                with dest.open("wb") as out:
                    shutil.copyfileobj(f.file, out)
                saved_files.append(dest)
            if not saved_files:
                raise ValueError("No PDF files uploaded.")
            return self.ingest_directory(str(tmp_path))


_ingestion_service: IngestionService | None = None


def get_ingestion_service() -> IngestionService:
    global _ingestion_service
    if _ingestion_service is None:
        _ingestion_service = IngestionService()
    return _ingestion_service


# ---------------------------------------------------------------------------
# CLI entry point (exposed via pyproject `rag-ingest`)
# ---------------------------------------------------------------------------


def cli() -> None:
    if len(sys.argv) < 2:
        raise SystemExit("Usage: rag-ingest <pdf_dir>")
    result = get_ingestion_service().ingest_directory(sys.argv[1])
    print(
        f"Ingested {result.files_ingested} file(s) → {result.chunks_added} chunks "
        f"into '{result.collection}' at '{result.persist_dir}'."
    )
