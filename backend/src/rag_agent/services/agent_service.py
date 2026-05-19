"""Agent orchestration service — the high-level entry point used by HTTP layer.

Encapsulates:
  - thread/session id management
  - sync invocation (``run``)
  - SSE-friendly streaming (``stream``)
  - resume after a human-in-the-loop interrupt (``resume``)
  - state inspection (``get_state``)
"""

from __future__ import annotations

import uuid
from typing import Any, AsyncIterator, Dict, List, Optional

from langchain_core.documents import Document
from langgraph.types import Command

from ..core.logging import get_logger
from ..models.schemas import (
    AgentRunResponse,
    DocumentPreview,
    HumanResumeRequest,
)
from ..models.state import AgentState, build_initial_state
from .workflow import get_compiled_graph

logger = get_logger(__name__)


def _doc_preview(doc: Document, *, relevance: Optional[str] = None,
                 score: Optional[float] = None) -> DocumentPreview:
    content = (doc.page_content or "").strip()
    return DocumentPreview(
        title=doc.metadata.get("title"),
        year=doc.metadata.get("year"),
        source=doc.metadata.get("source"),
        snippet=content[:400] + ("..." if len(content) > 400 else ""),
        relevance=relevance,
        score=score,
        origin=doc.metadata.get("origin"),
    )


def _previews_from_graded(graded) -> List[DocumentPreview]:
    return [
        _doc_preview(g["document"], relevance=g["relevance"], score=g["score"])
        for g in (graded or [])
    ]


def _state_to_response(thread_id: str, values: Dict[str, Any], *,
                       interrupted: bool = False,
                       interrupt_payload: Optional[Dict[str, Any]] = None) -> AgentRunResponse:
    return AgentRunResponse(
        thread_id=thread_id,
        question=values.get("question", ""),
        plan=values.get("plan"),
        final_answer=values.get("final_answer"),
        generation=values.get("generation"),
        needs_human_review=bool(values.get("needs_human_review")),
        human_feedback=values.get("human_feedback"),
        loop_step=values.get("loop_step", 0),
        documents=[_doc_preview(d) for d in (values.get("documents") or [])],
        graded_documents=_previews_from_graded(values.get("graded_documents")),
        web_results=[_doc_preview(d) for d in (values.get("web_results") or [])],
        error=values.get("error"),
        interrupted=interrupted,
        interrupt_payload=interrupt_payload,
    )


def _serialize_step(node_name: str, node_state: Dict[str, Any]) -> Dict[str, Any]:
    """Compact per-node SSE payload."""
    payload: Dict[str, Any] = {"node": node_name}
    if node_name == "plan_research":
        payload["plan"] = node_state.get("plan")
    elif node_name == "retrieve":
        payload["loop_step"] = node_state.get("loop_step")
        payload["docs"] = [_doc_preview(d).model_dump() for d in node_state.get("documents", [])]
    elif node_name == "grade_documents":
        graded = node_state.get("graded_documents") or []
        payload["relevant"] = sum(1 for g in graded if g["relevance"] == "relevant")
        payload["total"] = len(graded)
        payload["decision"] = node_state.get("relevance_decision")
    elif node_name == "transform_query":
        payload["question"] = node_state.get("question")
    elif node_name == "web_search":
        payload["web_results"] = [_doc_preview(d).model_dump()
                                   for d in node_state.get("web_results", [])]
    elif node_name == "generate":
        payload["generation"] = node_state.get("generation")
    elif node_name == "review_answer":
        payload["needs_human_review"] = node_state.get("needs_human_review")
        payload["feedback"] = node_state.get("human_feedback")
    elif node_name == "human_in_the_loop":
        payload["final_answer"] = node_state.get("final_answer")
    if node_state.get("error"):
        payload["error"] = node_state["error"]
    return payload


# ---------------------------------------------------------------------------
# Service class
# ---------------------------------------------------------------------------


class AgentService:
    def __init__(self) -> None:
        self._graph = get_compiled_graph()

    # ---- helpers -------------------------------------------------------
    @staticmethod
    def new_thread_id() -> str:
        return uuid.uuid4().hex

    def _cfg(self, thread_id: str) -> Dict[str, Any]:
        return {"configurable": {"thread_id": thread_id}}

    # ---- sync run ------------------------------------------------------
    def run(self, question: str, *, prompt_variant: str = "A",
            thread_id: Optional[str] = None) -> AgentRunResponse:
        thread_id = thread_id or self.new_thread_id()
        initial = build_initial_state(question, prompt_variant=prompt_variant)  # type: ignore[arg-type]
        config = self._cfg(thread_id)

        interrupted = False
        interrupt_payload: Optional[Dict[str, Any]] = None
        for step in self._graph.stream(initial, config=config):
            if "__interrupt__" in step:
                interrupted = True
                interrupt_payload = step["__interrupt__"][0].value
                break

        values = self._graph.get_state(config).values or {}
        return _state_to_response(
            thread_id, values,
            interrupted=interrupted, interrupt_payload=interrupt_payload,
        )

    # ---- resume --------------------------------------------------------
    def resume(self, thread_id: str, payload: HumanResumeRequest) -> AgentRunResponse:
        config = self._cfg(thread_id)
        resume_value: Dict[str, Any] = {
            "action": payload.action,
            "edited_answer": payload.edited_answer,
            "new_question": payload.new_question,
            "feedback": payload.feedback,
        }
        interrupted = False
        interrupt_payload: Optional[Dict[str, Any]] = None
        for step in self._graph.stream(Command(resume=resume_value), config=config):
            if "__interrupt__" in step:
                interrupted = True
                interrupt_payload = step["__interrupt__"][0].value
                break
        values = self._graph.get_state(config).values or {}
        return _state_to_response(
            thread_id, values,
            interrupted=interrupted, interrupt_payload=interrupt_payload,
        )

    # ---- inspect state -------------------------------------------------
    def get_state(self, thread_id: str) -> AgentRunResponse:
        config = self._cfg(thread_id)
        values = self._graph.get_state(config).values or {}
        return _state_to_response(thread_id, values)

    # ---- async SSE stream ---------------------------------------------
    async def stream(
        self,
        question: str,
        *,
        prompt_variant: str = "A",
        thread_id: Optional[str] = None,
    ) -> AsyncIterator[Dict[str, Any]]:
        """Yield SSE-shaped dicts: ``{"event": str, "data": dict}``."""
        thread_id = thread_id or self.new_thread_id()
        initial = build_initial_state(question, prompt_variant=prompt_variant)  # type: ignore[arg-type]
        config = self._cfg(thread_id)

        yield {"event": "meta", "data": {"thread_id": thread_id}}

        async for step in self._graph.astream(initial, config=config):
            if "__interrupt__" in step:
                intr = step["__interrupt__"][0]
                yield {
                    "event": "interrupt",
                    "data": {"thread_id": thread_id, "interrupt": intr.value},
                }
                return
            for node_name, node_state in step.items():
                yield {"event": "update", "data": _serialize_step(node_name, node_state)}

        values = self._graph.get_state(config).values or {}
        yield {
            "event": "final",
            "data": {
                "thread_id": thread_id,
                "final_answer": values.get("final_answer") or values.get("generation"),
                "error": values.get("error"),
            },
        }

    async def stream_resume(
        self, thread_id: str, payload: HumanResumeRequest,
    ) -> AsyncIterator[Dict[str, Any]]:
        config = self._cfg(thread_id)
        resume_value = {
            "action": payload.action,
            "edited_answer": payload.edited_answer,
            "new_question": payload.new_question,
            "feedback": payload.feedback,
        }
        yield {"event": "meta", "data": {"thread_id": thread_id, "resume": True}}
        async for step in self._graph.astream(Command(resume=resume_value), config=config):
            if "__interrupt__" in step:
                intr = step["__interrupt__"][0]
                yield {
                    "event": "interrupt",
                    "data": {"thread_id": thread_id, "interrupt": intr.value},
                }
                return
            for node_name, node_state in step.items():
                yield {"event": "update", "data": _serialize_step(node_name, node_state)}
        values = self._graph.get_state(config).values or {}
        yield {
            "event": "final",
            "data": {
                "thread_id": thread_id,
                "final_answer": values.get("final_answer") or values.get("generation"),
                "error": values.get("error"),
            },
        }


_agent_service: Optional[AgentService] = None


def get_agent_service() -> AgentService:
    global _agent_service
    if _agent_service is None:
        _agent_service = AgentService()
    return _agent_service
