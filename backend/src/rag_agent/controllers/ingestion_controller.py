"""Corpus ingestion endpoints."""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from ..models.schemas import IngestDirectoryRequest, IngestResponse
from ..services.ingestion_service import IngestionService, get_ingestion_service

router = APIRouter(prefix="/api/ingest", tags=["ingest"])


@router.post("/pdfs", response_model=IngestResponse)
def ingest_directory(
    payload: IngestDirectoryRequest,
    service: IngestionService = Depends(get_ingestion_service),
) -> IngestResponse:
    try:
        return service.ingest_directory(payload.pdf_dir)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/upload", response_model=IngestResponse)
async def ingest_uploads(
    files: List[UploadFile] = File(...),
    service: IngestionService = Depends(get_ingestion_service),
) -> IngestResponse:
    try:
        return await service.ingest_uploads(files)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
