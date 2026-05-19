"""LangGraph state graph assembly + routing.

Topology:

    START → plan_research → retrieve → grade_documents
                                              │
                                              ├─ generate ───► review_answer ──► [hil?] ──► END
                                              ├─ transform_query ───► retrieve  (loop)
                                              └─ web_search   ───► generate
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from ..core.config import get_settings
from ..core.logging import get_logger
from ..models.state import AgentState
from . import nodes

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------


def route_after_grading(
    state: AgentState,
) -> Literal["generate", "transform_query", "web_search"]:
    settings = get_settings()
    decision = state.get("relevance_decision") or "generate"
    loop_step = state.get("loop_step", 0)

    if loop_step >= settings.max_retrieve_iterations and decision == "transform_query":
        logger.warning("ROUTER | loop cap reached — overriding to web_search")
        return "web_search"

    return decision  # type: ignore[return-value]


def route_after_review(state: AgentState) -> Literal["human_in_the_loop", "end"]:
    return "human_in_the_loop" if state.get("needs_human_review") else "end"


def route_after_human(state: AgentState) -> Literal["retrieve", "end"]:
    return "end" if state.get("final_answer") is not None else "retrieve"


# ---------------------------------------------------------------------------
# Build & cache the compiled graph
# ---------------------------------------------------------------------------


def _build_graph():
    g = StateGraph(AgentState)

    g.add_node("plan_research", nodes.plan_research)
    g.add_node("retrieve", nodes.retrieve)
    g.add_node("grade_documents", nodes.grade_documents)
    g.add_node("transform_query", nodes.transform_query)
    g.add_node("web_search", nodes.search_web)
    g.add_node("generate", nodes.generate)
    g.add_node("review_answer", nodes.review_answer)
    g.add_node("human_in_the_loop", nodes.human_in_the_loop)

    g.add_edge(START, "plan_research")
    g.add_edge("plan_research", "retrieve")
    g.add_edge("retrieve", "grade_documents")
    g.add_edge("transform_query", "retrieve")
    g.add_edge("web_search", "generate")
    g.add_edge("generate", "review_answer")

    g.add_conditional_edges(
        source="grade_documents",
        path=route_after_grading,
        path_map={
            "generate": "generate",
            "transform_query": "transform_query",
            "web_search": "web_search",
        },
    )
    g.add_conditional_edges(
        source="review_answer",
        path=route_after_review,
        path_map={"human_in_the_loop": "human_in_the_loop", "end": END},
    )
    g.add_conditional_edges(
        source="human_in_the_loop",
        path=route_after_human,
        path_map={"retrieve": "retrieve", "end": END},
    )

    return g.compile(checkpointer=MemorySaver())


@lru_cache(maxsize=1)
def get_compiled_graph():
    return _build_graph()
