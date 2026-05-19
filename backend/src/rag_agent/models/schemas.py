"""HTTP request / response DTOs exchanged with the Angular frontend."""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Agent run
# ---------------------------------------------------------------------------


class AgentRunRequest(BaseModel):
    question: str = Field(..., min_length=1)
    prompt_variant: Literal["A", "B"] = "A"
    thread_id: Optional[str] = Field(
        default=None,
        description="Optional client-supplied thread id (for resumable sessions).",
    )


class DocumentPreview(BaseModel):
    title: Optional[str] = None
    year: Optional[Any] = None
    source: Optional[str] = None
    snippet: str = ""
    score: Optional[float] = None
    relevance: Optional[str] = None
    origin: Optional[Literal["vector", "web"]] = None


class AgentRunResponse(BaseModel):
    thread_id: str
    question: str
    plan: Optional[str] = None
    final_answer: Optional[str] = None
    generation: Optional[str] = None
    needs_human_review: bool = False
    human_feedback: Optional[str] = None
    loop_step: int = 0
    documents: List[DocumentPreview] = []
    graded_documents: List[DocumentPreview] = []
    web_results: List[DocumentPreview] = []
    error: Optional[str] = None
    interrupted: bool = False
    interrupt_payload: Optional[Dict[str, Any]] = None


class HumanResumeRequest(BaseModel):
    action: Literal["approve", "edit_answer", "revise_query"] = "approve"
    edited_answer: Optional[str] = None
    new_question: Optional[str] = None
    feedback: Optional[str] = None


# ---------------------------------------------------------------------------
# Ingestion
# ---------------------------------------------------------------------------


class IngestDirectoryRequest(BaseModel):
    pdf_dir: str = Field(..., description="Absolute or relative path to a folder of PDFs.")


class IngestResponse(BaseModel):
    files_ingested: int
    chunks_added: int
    collection: str
    persist_dir: str


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------


class EvaluationRequest(BaseModel):
    questions: List[str] = Field(..., min_length=1)
    variants: List[Literal["A", "B"]] = Field(default_factory=lambda: ["A", "B"])


class VariantScores(BaseModel):
    answer_relevance: float
    groundedness: float
    overall: float


class EvaluationResponse(BaseModel):
    summary: Dict[str, VariantScores]


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
    provider: str
    model: str
    chroma_collection: str
    chroma_persist_dir: str
    web_search_provider: str
