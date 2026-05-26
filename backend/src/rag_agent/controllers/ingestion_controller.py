"""Corpus ingestion endpoints."""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from ..core.logging import get_logger
from ..models.schemas import (
    CorpusEntry,
    CorpusListResponse,
    IngestDirectoryRequest,
    IngestResponse,
)
from ..repositories.vector_repository import get_vector_repository
from ..services.ingestion_service import IngestionService, get_ingestion_service

logger = get_logger(__name__)
router = APIRouter(prefix="/api/ingest", tags=["ingest"])


def _handle(exc: Exception) -> "HTTPException":
    """Translate a service-layer exception into an HTTPException with a useful
    ``detail`` body so the Angular client can render the real cause."""
    if isinstance(exc, ValueError):
        return HTTPException(status_code=400, detail=str(exc))
    logger.error("INGEST | %s: %s", type(exc).__name__, exc, exc_info=True)
    return HTTPException(status_code=500, detail=f"{type(exc).__name__}: {exc}")


@router.post("/pdfs", response_model=IngestResponse)
def ingest_directory(
    payload: IngestDirectoryRequest,
    service: IngestionService = Depends(get_ingestion_service),
) -> IngestResponse:
    try:
        return service.ingest_directory(payload.pdf_dir)
    except Exception as exc:  # noqa: BLE001
        raise _handle(exc) from exc


@router.post("/upload", response_model=IngestResponse)
async def ingest_uploads(
    files: List[UploadFile] = File(...),
    service: IngestionService = Depends(get_ingestion_service),
) -> IngestResponse:
    try:
        return await service.ingest_uploads(files)
    except Exception as exc:  # noqa: BLE001
        raise _handle(exc) from exc


@router.get("/corpus", response_model=CorpusListResponse)
def list_corpus() -> CorpusListResponse:
    """List every distinct document currently indexed in ChromaDB."""
    repo = get_vector_repository()
    entries = [CorpusEntry(**e) for e in repo.list_documents()]
    return CorpusListResponse(
        collection=repo.collection,
        total_docs=len(entries),
        total_chunks=sum(e.chunks for e in entries),
        documents=entries,
    )
