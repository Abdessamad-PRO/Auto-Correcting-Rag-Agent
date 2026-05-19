"""LangGraph TypedDict state — canonical shared state across all nodes."""

from __future__ import annotations

from typing import List, Literal, Optional, TypedDict

from langchain_core.documents import Document


class GradedDocument(TypedDict):
    document: Document
    relevance: Literal["relevant", "irrelevant"]
    score: float


class AgentState(TypedDict, total=False):
    """Canonical state object shared across every LangGraph node.

    All fields are declared as optional (``total=False``) so the LangGraph
    reducer can merge partial updates from each node.
    """

    # --- Prompt / planning ----------------------------------------------
    prompt_variant: Optional[Literal["A", "B"]]
    plan: Optional[str]

    # --- Core research fields -------------------------------------------
    question: str
    original_question: str
    documents: List[Document]
    graded_documents: List[GradedDocument]
    web_results: List[Document]
    generation: Optional[str]

    # --- Routing / safety ------------------------------------------------
    loop_step: int
    relevance_decision: Optional[Literal["generate", "transform_query", "web_search"]]

    # --- Human-in-the-loop ----------------------------------------------
    needs_human_review: bool
    human_feedback: Optional[str]
    final_answer: Optional[str]

    # --- Observability ---------------------------------------------------
    error: Optional[str]


def build_initial_state(
    question: str,
    *,
    prompt_variant: Literal["A", "B"] = "A",
) -> AgentState:
    """Construct a fully-initialised AgentState for a new session."""
    return AgentState(
        prompt_variant=prompt_variant,
        plan=None,
        question=question,
        original_question=question,
        documents=[],
        graded_documents=[],
        web_results=[],
        generation=None,
        loop_step=0,
        relevance_decision=None,
        needs_human_review=False,
        human_feedback=None,
        final_answer=None,
        error=None,
    )
