"""Prompt-evaluation endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from ..models.schemas import EvaluationRequest, EvaluationResponse
from ..services.evaluation_service import EvaluationService, get_evaluation_service

router = APIRouter(prefix="/api/evaluate", tags=["evaluate"])


@router.post("", response_model=EvaluationResponse)
def evaluate(
    payload: EvaluationRequest,
    service: EvaluationService = Depends(get_evaluation_service),
) -> EvaluationResponse:
    return service.evaluate(payload)
