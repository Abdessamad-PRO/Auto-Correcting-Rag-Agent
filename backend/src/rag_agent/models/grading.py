"""Pydantic schemas for structured LLM outputs."""

from __future__ import annotations

from pydantic import BaseModel, Field


class RelevanceGrade(BaseModel):
    binary_score: str = Field(
        description="Exactly 'yes' if the document is relevant, otherwise 'no'."
    )
    confidence: float = Field(
        ge=0.0, le=1.0, description="Confidence in the verdict in [0,1]."
    )
    rationale: str = Field(description="One-sentence justification.")


class TransformedQuery(BaseModel):
    improved_query: str = Field(description="Semantically enriched reformulation.")
    reasoning: str = Field(description="Why the transformation should help retrieval.")


class ResearchPlan(BaseModel):
    plan: str = Field(
        description="Short hierarchical plan (3-7 steps) for the research mission."
    )


class AnswerReview(BaseModel):
    needs_human_review: bool = Field(
        description="True if the answer is risky / under-grounded and needs human input."
    )
    feedback: str = Field(description="Brief actionable feedback.")
