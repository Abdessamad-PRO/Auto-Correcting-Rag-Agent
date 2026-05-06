# =============================================================================
# FILE: state.py
# PROJECT: Auto-Correcting Academic Research Agent
# DESCRIPTION: Defines the canonical AgentState TypedDict that flows through
#              every node of the LangGraph workflow. This is the single source
#              of truth for all inter-node communication.
# AUTHOR: ENSET Master's Project — Distributed Systems & AI
# =============================================================================

from __future__ import annotations

from typing import List, Literal, Optional, TypedDict

from langchain_core.documents import Document


# ---------------------------------------------------------------------------
# Grading Schema
# ---------------------------------------------------------------------------

class GradedDocument(TypedDict):
    """
    A wrapper around a retrieved Document that carries an explicit relevance
    label assigned by the Grader node.

    Attributes
    ----------
    document : Document
        The raw LangChain Document object (page_content + metadata).
    relevance : Literal["relevant", "irrelevant"]
        Binary relevance verdict produced by the LLM grader.
    score : float
        Continuous confidence score in [0.0, 1.0]. Values ≥ 0.5 map to
        "relevant"; values < 0.5 map to "irrelevant".
    """

    document: Document
    relevance: Literal["relevant", "irrelevant"]
    score: float


# ---------------------------------------------------------------------------
# Primary Agent State
# ---------------------------------------------------------------------------

class AgentState(TypedDict):
    """
    Immutable-by-convention state object shared across all LangGraph nodes.

    The graph transitions by returning partial dictionaries from each node;
    LangGraph merges these partials into the canonical state using its
    built-in reducer logic.

    Safety
    ------
    ``loop_step`` is a mandatory counter that prevents infinite
    Retrieve → Grade → Rewrite → Retrieve cycles. Any node that initiates
    a retrieval cycle must increment this value.  The router in
    ``workflow.py`` will force an early termination path once
    ``loop_step >= MAX_RETRIEVE_ITERATIONS`` (currently 3).

    Attributes
    ----------
    question : str
        The original (or most recently transformed) research question
        issued by the user or derived by the Query Transformer node.
    original_question : str
        Preserved verbatim copy of the user's initial question. Immutable
        after initialisation; used for drift-detection in the transformer.
    documents : List[Document]
        Raw documents returned by the most recent retrieval call.
    graded_documents : List[GradedDocument]
        Annotated documents produced by the Grader node.
    generation : Optional[str]
        The final synthesised answer produced by the Generator node.
        ``None`` until the Generator has run at least once.
    loop_step : int
        Zero-indexed iteration counter for the Retrieve → Grade cycle.
        Initialised to 0; incremented in ``retrieve`` node.
        Hard cap enforced by the conditional router in ``workflow.py``.
    relevance_decision : Optional[Literal["generate", "transform_query"]]
        Routing signal written by the ``grade_documents`` node after
        evaluating corpus quality. Consumed by the conditional edge
        ``route_after_grading``.
    error : Optional[str]
        Optional human-readable error message for observability.
        Populated by any node that catches a recoverable exception.
    """

    # Core research fields
    question: str
    original_question: str
    documents: List[Document]
    graded_documents: List[GradedDocument]
    generation: Optional[str]

    # Safety & routing control fields
    loop_step: int
    relevance_decision: Optional[Literal["generate", "transform_query"]]

    # Observability
    error: Optional[str]


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: Maximum number of Retrieve → Grade → Rewrite cycles before the workflow
#: forces generation on whatever documents are available. Modifying this
#: value requires a corresponding update to the router in workflow.py.
MAX_RETRIEVE_ITERATIONS: int = 3

#: Minimum fraction of graded documents that must be deemed "relevant"
#: for the workflow to proceed directly to generation (bypassing rewrite).
RELEVANCE_THRESHOLD: float = 0.5
