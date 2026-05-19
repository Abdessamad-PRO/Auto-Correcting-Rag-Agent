"""LangGraph node functions.

Each node receives the whole :class:`AgentState` and returns a partial dict
update; LangGraph's reducer merges the partials into the next state.
"""

from __future__ import annotations

from typing import Any, Dict, List

from langchain_core.documents import Document
from langgraph.types import interrupt

from ..core.config import get_settings
from ..core.logging import get_logger
from ..models.grading import (
    AnswerReview,
    RelevanceGrade,
    ResearchPlan,
    TransformedQuery,
)
from ..models.state import AgentState, GradedDocument
from ..repositories.vector_repository import get_vector_repository
from . import chains
from .tools.web_search import web_search

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# plan_research
# ---------------------------------------------------------------------------


def plan_research(state: AgentState) -> Dict[str, Any]:
    logger.info("NODE:plan_research | question='%s'", state["question"])
    try:
        result: ResearchPlan = chains.planner_chain().invoke({"question": state["question"]})
        return {"plan": result.plan, "error": None}
    except Exception as exc:  # noqa: BLE001
        logger.error("NODE:plan_research | exception: %s", exc, exc_info=True)
        return {"plan": None, "error": f"Planning failure: {exc}"}


# ---------------------------------------------------------------------------
# retrieve
# ---------------------------------------------------------------------------


def retrieve(state: AgentState) -> Dict[str, Any]:
    loop_step = state.get("loop_step", 0)
    logger.info(
        "NODE:retrieve | question='%s' | loop_step=%d", state["question"], loop_step
    )
    try:
        retriever = get_vector_repository().as_retriever()
        docs: List[Document] = retriever.invoke(state["question"])
        for d in docs:
            d.metadata.setdefault("origin", "vector")
        logger.info("NODE:retrieve | retrieved %d document(s)", len(docs))
        return {"documents": docs, "loop_step": loop_step + 1, "error": None}
    except Exception as exc:  # noqa: BLE001
        logger.error("NODE:retrieve | exception: %s", exc, exc_info=True)
        return {
            "documents": [],
            "loop_step": loop_step + 1,
            "error": f"Retrieval failure: {exc}",
        }


# ---------------------------------------------------------------------------
# grade_documents
# ---------------------------------------------------------------------------


def grade_documents(state: AgentState) -> Dict[str, Any]:
    settings = get_settings()
    docs = state.get("documents", []) or []
    loop_step = state.get("loop_step", 0)
    logger.info("NODE:grade_documents | grading %d doc(s) | loop_step=%d", len(docs), loop_step)

    graded: List[GradedDocument] = []
    for doc in docs:
        try:
            grade: RelevanceGrade = chains.grader_chain().invoke(
                {"question": state["question"], "document": doc.page_content}
            )
            relevance = "relevant" if grade.binary_score.lower() == "yes" else "irrelevant"
            score = grade.confidence if relevance == "relevant" else 1.0 - grade.confidence
            graded.append(GradedDocument(document=doc, relevance=relevance, score=score))
        except Exception as exc:  # noqa: BLE001
            logger.warning("  grading failed for one document: %s", exc)
            graded.append(GradedDocument(document=doc, relevance="irrelevant", score=0.0))

    n_rel = sum(1 for g in graded if g["relevance"] == "relevant")
    fraction = (n_rel / len(graded)) if graded else 0.0
    logger.info(
        "NODE:grade_documents | relevant=%d/%d (%.0f%%)", n_rel, len(graded), fraction * 100
    )

    if loop_step >= settings.max_retrieve_iterations:
        # Final iteration — if still bad, escalate to web search instead of giving up.
        if fraction >= settings.relevance_threshold:
            decision = "generate"
        else:
            decision = "web_search"
            logger.warning(
                "NODE:grade_documents | MAX iterations reached with weak corpus — "
                "escalating to web_search."
            )
    elif fraction >= settings.relevance_threshold:
        decision = "generate"
    elif not graded:
        # Zero retrieval results — try the web before rewriting endlessly
        decision = "web_search"
    else:
        decision = "transform_query"

    logger.info("NODE:grade_documents | routing decision → '%s'", decision)
    return {"graded_documents": graded, "relevance_decision": decision}


# ---------------------------------------------------------------------------
# transform_query
# ---------------------------------------------------------------------------


def transform_query(state: AgentState) -> Dict[str, Any]:
    logger.info(
        "NODE:transform_query | original='%s' | current='%s'",
        state.get("original_question"),
        state["question"],
    )
    try:
        result: TransformedQuery = chains.transformer_chain().invoke(
            {
                "original_question": state["original_question"],
                "question": state["question"],
            }
        )
        logger.info("NODE:transform_query | improved='%s'", result.improved_query)
        return {"question": result.improved_query, "error": None}
    except Exception as exc:  # noqa: BLE001
        logger.error("NODE:transform_query | exception: %s", exc, exc_info=True)
        return {
            "question": state.get("original_question", state["question"]),
            "error": f"Query transformation failure: {exc}",
        }


# ---------------------------------------------------------------------------
# web_search
# ---------------------------------------------------------------------------


def search_web(state: AgentState) -> Dict[str, Any]:
    """Web search node — invoked when the corpus is exhausted or empty.

    Merges the web hits with whatever graded documents we already have, so
    ``generate`` can ground its answer on both sources of evidence.
    """
    logger.info("NODE:web_search | querying the web for: '%s'", state["question"])
    results = web_search(state["question"])
    # Promote web results into the graded pool as 'relevant' (the web tool
    # has already filtered for topical hits).
    new_graded: List[GradedDocument] = list(state.get("graded_documents", []) or [])
    for d in results:
        new_graded.append(GradedDocument(document=d, relevance="relevant", score=0.7))
    return {
        "web_results": results,
        "graded_documents": new_graded,
        "error": None,
    }


# ---------------------------------------------------------------------------
# generate
# ---------------------------------------------------------------------------


def _format_context(docs: List[Document]) -> str:
    return "\n\n---\n\n".join(
        f"[Source: {d.metadata.get('title', 'Unknown')} "
        f"({d.metadata.get('year', d.metadata.get('source', 'n.d.'))})] \n{d.page_content}"
        for d in docs
    )


def generate(state: AgentState) -> Dict[str, Any]:
    logger.info("NODE:generate | composing synthesis...")
    graded = state.get("graded_documents") or []
    if graded:
        context_docs = [g["document"] for g in graded if g["relevance"] == "relevant"]
        if not context_docs:
            context_docs = [g["document"] for g in graded]
    else:
        context_docs = state.get("documents") or []

    context_str = _format_context(context_docs)
    chain = chains.generator_chain(state.get("prompt_variant") or "A")

    try:
        answer = chain.invoke({"question": state["question"], "context": context_str})
        logger.info("NODE:generate | %d chars generated", len(answer))
        return {"generation": answer, "error": None}
    except Exception as exc:  # noqa: BLE001
        logger.error("NODE:generate | exception: %s", exc, exc_info=True)
        return {
            "generation": "Generation failed due to an internal error.",
            "error": f"Generation failure: {exc}",
        }


# ---------------------------------------------------------------------------
# review_answer
# ---------------------------------------------------------------------------


def review_answer(state: AgentState) -> Dict[str, Any]:
    logger.info("NODE:review_answer | running safety/faithfulness review...")
    if not state.get("generation"):
        return {
            "needs_human_review": True,
            "human_feedback": "No generation produced; human validation required.",
        }
    graded = state.get("graded_documents") or []
    if graded:
        context_docs = [g["document"] for g in graded if g["relevance"] == "relevant"]
        if not context_docs:
            context_docs = [g["document"] for g in graded]
    else:
        context_docs = state.get("documents") or []
    context_str = _format_context(context_docs)

    try:
        review: AnswerReview = chains.reviewer_chain().invoke(
            {
                "question": state["question"],
                "context": context_str,
                "answer": state["generation"],
            }
        )
        return {
            "needs_human_review": bool(review.needs_human_review),
            "human_feedback": review.feedback,
        }
    except Exception as exc:  # noqa: BLE001
        logger.error("NODE:review_answer | exception: %s", exc, exc_info=True)
        return {"needs_human_review": True, "human_feedback": f"Review failure: {exc}"}


# ---------------------------------------------------------------------------
# human_in_the_loop  (LangGraph interrupt)
# ---------------------------------------------------------------------------


def human_in_the_loop(state: AgentState) -> Dict[str, Any]:
    logger.info("NODE:human_in_the_loop | awaiting human validation...")
    payload = {
        "type": "human_review",
        "question": state.get("question"),
        "plan": state.get("plan"),
        "draft_answer": state.get("generation"),
        "review_feedback": state.get("human_feedback"),
        "error": state.get("error"),
        "actions": ["approve", "edit_answer", "revise_query"],
    }
    resume_value = interrupt(payload) or {}
    action = (resume_value.get("action") or "approve").strip().lower()
    feedback = (resume_value.get("feedback") or "").strip() or None

    if action == "edit_answer":
        edited = (resume_value.get("edited_answer") or "").strip()
        final = edited or (state.get("generation") or "")
        return {
            "final_answer": final,
            "human_feedback": feedback,
            "needs_human_review": False,
        }

    if action == "revise_query":
        new_q = (resume_value.get("new_question") or "").strip() or state["question"]
        return {
            "question": new_q,
            "human_feedback": feedback,
            "final_answer": None,
            "needs_human_review": False,
        }

    # approve
    return {
        "final_answer": state.get("generation") or "",
        "human_feedback": feedback,
        "needs_human_review": False,
    }
