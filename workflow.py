# =============================================================================
# FILE: workflow.py
# PROJECT: Auto-Correcting Academic Research Agent
# DESCRIPTION: Assembles the LangGraph StateGraph, wires all nodes and edges,
#              and exposes the compiled graph as the public interface.
#              Also provides a CLI entry point for interactive research queries.
# AUTHOR: ENSET Master's Project — Distributed Systems & AI
# =============================================================================

from __future__ import annotations

import sys
import logging
from typing import Literal

from langgraph.graph import END, START, StateGraph

from nodes import generate, grade_documents, retrieve, transform_query
from state import AgentState, MAX_RETRIEVE_ITERATIONS

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Conditional Edge Router
# ---------------------------------------------------------------------------


def route_after_grading(
    state: AgentState,
) -> Literal["generate", "transform_query"]:
    """
    Conditional edge function: routes the workflow after the Grader node.

    This function is registered as a ``conditional_edge`` and is invoked by
    LangGraph after every execution of the ``grade_documents`` node. It reads
    the ``relevance_decision`` field written by the grader and returns the
    name of the next node to execute.

    Circuit-Breaker Safety
    ----------------------
    Although ``grade_documents`` already enforces the iteration cap by setting
    ``relevance_decision = "generate"`` when ``loop_step >= MAX_RETRIEVE_ITERATIONS``,
    this router adds a redundant check as a defense-in-depth measure. If the
    state somehow still requests ``"transform_query"`` at or beyond the cap,
    the router overrides and forces ``"generate"``.

    Parameters
    ----------
    state : AgentState
        Current graph state. Must contain ``relevance_decision`` and
        ``loop_step``.

    Returns
    -------
    Literal["generate", "transform_query"]
        Name of the next node to execute. LangGraph uses this string to
        resolve the conditional edge target.
    """
    decision = state.get("relevance_decision", "generate")

    # Redundant safety check
    if state["loop_step"] >= MAX_RETRIEVE_ITERATIONS and decision == "transform_query":
        logger.warning(
            "ROUTER | loop_step=%d >= MAX=%d — overriding '%s' → 'generate'",
            state["loop_step"],
            MAX_RETRIEVE_ITERATIONS,
            decision,
        )
        return "generate"

    logger.info(
        "ROUTER | loop_step=%d | routing → '%s'",
        state["loop_step"],
        decision,
    )
    return decision  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# Graph Assembly
# ---------------------------------------------------------------------------


def build_graph() -> StateGraph:
    """
    Construct and return the compiled LangGraph StateGraph.

    Graph Topology
    --------------
    ::

        START
          │
          ▼
       retrieve  ◄────────────────────────────────────┐
          │                                            │
          ▼                                            │
    grade_documents                                    │
          │                                            │
          ├─[relevance_decision == "generate"]──► generate ──► END
          │
          └─[relevance_decision == "transform_query"]─► transform_query
                                                              │
                                                              └──────────┘

    Nodes
    -----
    - ``retrieve``         : Vector-store document retrieval.
    - ``grade_documents``  : LLM-powered relevance grading.
    - ``transform_query``  : LLM-powered query reformulation.
    - ``generate``         : Academic synthesis / answer generation.

    Edges
    -----
    - ``START → retrieve``                        : Unconditional.
    - ``retrieve → grade_documents``              : Unconditional.
    - ``grade_documents → {generate | transform_query}`` : Conditional via
      ``route_after_grading``.
    - ``transform_query → retrieve``              : Unconditional (closes cycle).
    - ``generate → END``                          : Unconditional.

    Returns
    -------
    StateGraph
        The compiled, executable LangGraph graph object. Call ``.invoke()``
        or ``.stream()`` on this object to run the agent.
    """
    # ── Initialise graph with typed state schema ──────────────────────────
    workflow = StateGraph(AgentState)

    # ── Register nodes ────────────────────────────────────────────────────
    workflow.add_node("retrieve", retrieve)
    workflow.add_node("grade_documents", grade_documents)
    workflow.add_node("transform_query", transform_query)
    workflow.add_node("generate", generate)

    # ── Wire unconditional edges ──────────────────────────────────────────
    workflow.add_edge(START, "retrieve")
    workflow.add_edge("retrieve", "grade_documents")
    workflow.add_edge("transform_query", "retrieve")  # Close the feedback loop
    workflow.add_edge("generate", END)

    # ── Wire conditional edges ────────────────────────────────────────────
    workflow.add_conditional_edges(
        source="grade_documents",
        path=route_after_grading,
        path_map={
            "generate": "generate",
            "transform_query": "transform_query",
        },
    )

    return workflow.compile()


# ---------------------------------------------------------------------------
# Public Graph Instance
# ---------------------------------------------------------------------------

#: Module-level compiled graph — import this in downstream modules or
#: Jupyter notebooks to invoke the agent.
graph = build_graph()


# ---------------------------------------------------------------------------
# Initialisation Helper
# ---------------------------------------------------------------------------


def _build_initial_state(question: str) -> AgentState:
    """
    Construct a fully-initialised ``AgentState`` for a new research session.

    Parameters
    ----------
    question : str
        The raw research question from the user.

    Returns
    -------
    AgentState
        A valid initial state dict with all required fields populated and
        all counters / accumulators reset to their zero values.
    """
    return AgentState(
        question=question,
        original_question=question,
        documents=[],
        graded_documents=[],
        generation=None,
        loop_step=0,
        relevance_decision=None,
        error=None,
    )


# ---------------------------------------------------------------------------
# Stream Execution Helper
# ---------------------------------------------------------------------------


def run_research_query(question: str, stream: bool = True) -> str:
    """
    Execute a single research query through the agent graph.

    Parameters
    ----------
    question : str
        Natural-language research question.
    stream : bool, optional
        If ``True`` (default), stream intermediate node outputs to stdout
        for real-time observability. If ``False``, invoke synchronously and
        return only the final generation.

    Returns
    -------
    str
        The synthesised academic answer from the Generator node.
    """
    initial_state = _build_initial_state(question)

    if stream:
        print("\n" + "═" * 72)
        print(f"  AUTO-CORRECTING RESEARCH AGENT")
        print(f"  Query: {question}")
        print("═" * 72 + "\n")

        final_state = None
        for step_output in graph.stream(initial_state):
            for node_name, node_state in step_output.items():
                print(f"  ▶  [{node_name.upper()}]")
                if node_name == "retrieve":
                    print(
                        f"     Retrieved {len(node_state.get('documents', []))} "
                        f"document(s)  |  loop_step → {node_state.get('loop_step', '?')}"
                    )
                elif node_name == "grade_documents":
                    graded = node_state.get("graded_documents", [])
                    n_rel = sum(1 for g in graded if g["relevance"] == "relevant")
                    print(
                        f"     Relevant: {n_rel}/{len(graded)}  |  "
                        f"decision → {node_state.get('relevance_decision', '?')}"
                    )
                elif node_name == "transform_query":
                    print(f"     New query: {node_state.get('question', '?')}")
                elif node_name == "generate":
                    gen = node_state.get("generation", "")
                    print(f"     Generation: {len(gen)} chars")
                    final_state = node_state
                print()

        answer = (final_state or {}).get("generation", "No answer generated.")
        print("═" * 72)
        print("  SYNTHESISED ANSWER\n")
        print(answer)
        print("═" * 72 + "\n")
        return answer

    else:
        final_state = graph.invoke(initial_state)
        return final_state.get("generation", "No answer generated.")


# ---------------------------------------------------------------------------
# CLI Entry Point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    default_question = (
        "How do Graph Convolutional Networks leverage the non-Euclidean topology "
        "of EEG electrode configurations to improve motor imagery classification "
        "accuracy, and what spectral graph convolution methods have proven most "
        "effective in recent BCI literature?"
    )

    query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else default_question
    run_research_query(query, stream=True)
