# =============================================================================
# FILE: nodes.py
# PROJECT: Auto-Correcting Academic Research Agent
# DESCRIPTION: Implements all LangGraph node functions. Each function accepts
#              an AgentState dict and returns a partial state dict that
#              LangGraph merges via its built-in reducer.
# AUTHOR: ENSET Master's Project — Distributed Systems & AI
# =============================================================================

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List

from langchain.prompts import ChatPromptTemplate
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from pydantic import BaseModel, Field

from state import (
    MAX_RETRIEVE_ITERATIONS,
    RELEVANCE_THRESHOLD,
    AgentState,
    GradedDocument,
)

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  [%(levelname)s]  %(name)s — %(message)s",
)

# ---------------------------------------------------------------------------
# Shared LLM & Embedding Instances
# ---------------------------------------------------------------------------

_LLM_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o")
_EMBED_MODEL: str = os.getenv("OPENAI_EMBED_MODEL", "text-embedding-3-small")
_CHROMA_DIR: str = os.getenv("CHROMA_PERSIST_DIR", "./chroma_db")
_COLLECTION: str = os.getenv("CHROMA_COLLECTION", "gcn_eeg_papers")
_TOP_K: int = int(os.getenv("RETRIEVER_TOP_K", "5"))

llm = ChatOpenAI(model=_LLM_MODEL, temperature=0)
embeddings = OpenAIEmbeddings(model=_EMBED_MODEL)


# ---------------------------------------------------------------------------
# Pydantic Schemas for Structured Outputs
# ---------------------------------------------------------------------------


class RelevanceGrade(BaseModel):
    """
    Structured output produced by the document relevance grader.

    The LLM is forced to emit a valid instance of this schema via
    ``.with_structured_output()``, eliminating free-text parsing errors.
    """

    binary_score: str = Field(
        description=(
            "Relevance verdict. MUST be exactly 'yes' if the document "
            "contains information pertinent to the research question, "
            "or 'no' otherwise."
        )
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description=(
            "Grader confidence in the binary_score, expressed as a "
            "probability in [0.0, 1.0]."
        ),
    )
    rationale: str = Field(
        description=(
            "One-sentence justification for the assigned grade. "
            "Must reference specific concepts from the document."
        )
    )


class TransformedQuery(BaseModel):
    """
    Structured output produced by the query transformation node.
    """

    improved_query: str = Field(
        description=(
            "A semantically enriched reformulation of the original research "
            "question. Must incorporate domain-specific terminology relevant "
            "to Graph Convolutional Networks and EEG signal processing."
        )
    )
    reasoning: str = Field(
        description=(
            "Brief explanation of the transformations applied and the "
            "academic sub-domain they are intended to target."
        )
    )


# ---------------------------------------------------------------------------
# Prompt Templates
# ---------------------------------------------------------------------------

_GRADER_SYSTEM = """\
You are a specialist academic relevance assessor with deep expertise in:
  • Graph Neural Networks (GNN) and Graph Convolutional Networks (GCN)
  • Electroencephalography (EEG) signal processing and Brain-Computer Interfaces (BCI)
  • Deep learning architectures for time-series and graph-structured data

Your sole task is to determine whether a retrieved document chunk contains
information that is materially relevant to the provided research question.

Relevance criteria:
  1. The chunk discusses concepts, methods, datasets, or experimental results
     that directly address the question.
  2. Background information on prerequisite topics (e.g., spectral graph theory
     when the question concerns GCN) is acceptable if substantive.
  3. Tangential or unrelated domain content must be graded as irrelevant.

Be strict. Do not infer relevance that is not textually supported.\
"""

_GRADER_HUMAN = """\
Research Question:
{question}

Document Chunk:
{document}

Produce a structured relevance grade.\
"""

_GENERATOR_SYSTEM = """\
You are an elite academic research synthesiser embedded in a postgraduate
research pipeline at an Engineering School (ENSET). Your outputs will be
incorporated into a Master's dissertation on Graph Convolutional Networks
for EEG signal decoding.

Synthesis directives:
  1. Ground every claim in the provided context documents. Do not hallucinate
     citations or results.
  2. Use precise academic language: define acronyms on first use, employ
     hedging where appropriate (e.g., "the evidence suggests", "results
     indicate"), and maintain third-person formality.
  3. Structure the answer with an introduction, a body that systematically
     addresses sub-questions, and a concise conclusion that identifies
     remaining open questions.
  4. If the context is insufficient to fully answer the question, explicitly
     state the knowledge gap rather than fabricating information.
  5. Cite sources by their metadata ``title`` and ``year`` fields where
     available.\
"""

_GENERATOR_HUMAN = """\
Research Question:
{question}

Retrieved Context (ordered by relevance):
{context}

Synthesise a rigorous academic answer.\
"""

_TRANSFORMER_SYSTEM = """\
You are an expert academic search strategist specialising in information
retrieval for scientific literature on Graph Neural Networks and EEG
Brain-Computer Interfaces.

Your task is to reformulate an underperforming research query so that a
dense vector retriever will surface more relevant chunks from an academic
corpus. Apply the following transformation strategies as appropriate:

  1. **Terminology expansion**: Replace generic terms with domain-specific
     synonyms (e.g., "brain signals" → "EEG epochs / neural oscillations").
  2. **Concept decomposition**: Break composite questions into their core
     technical components.
  3. **Specificity injection**: Add relevant methodological qualifiers
     (e.g., spectral graph convolution, Chebyshev polynomial approximation,
     motor imagery classification).
  4. **Drift correction**: If the new query would stray too far from the
     original intent, anchor it with the original formulation.\
"""

_TRANSFORMER_HUMAN = """\
Original Research Question (preserve intent):
{original_question}

Current (underperforming) Query:
{question}

Produce an improved query.\
"""

# Compile prompt templates
grader_prompt = ChatPromptTemplate.from_messages(
    [("system", _GRADER_SYSTEM), ("human", _GRADER_HUMAN)]
)
generator_prompt = ChatPromptTemplate.from_messages(
    [("system", _GENERATOR_SYSTEM), ("human", _GENERATOR_HUMAN)]
)
transformer_prompt = ChatPromptTemplate.from_messages(
    [("system", _TRANSFORMER_SYSTEM), ("human", _TRANSFORMER_HUMAN)]
)

# ---------------------------------------------------------------------------
# Chain Instantiation
# ---------------------------------------------------------------------------

grader_chain = grader_prompt | llm.with_structured_output(RelevanceGrade)
generator_chain = generator_prompt | llm | StrOutputParser()
transformer_chain = transformer_prompt | llm.with_structured_output(
    TransformedQuery
)


# ---------------------------------------------------------------------------
# Helper: build retriever
# ---------------------------------------------------------------------------


def _build_retriever():
    """
    Instantiate and return a ChromaDB-backed retriever.

    The retriever uses Maximum Marginal Relevance (MMR) search to balance
    relevance against result diversity, which is critical for broad academic
    queries that span multiple sub-topics (e.g., graph signal processing,
    attention mechanisms, EEG artefact removal).

    Returns
    -------
    VectorStoreRetriever
        Configured retriever instance.
    """
    vectorstore = Chroma(
        collection_name=_COLLECTION,
        embedding_function=embeddings,
        persist_directory=_CHROMA_DIR,
    )
    return vectorstore.as_retriever(
        search_type="mmr",
        search_kwargs={"k": _TOP_K, "fetch_k": _TOP_K * 3, "lambda_mult": 0.7},
    )


# Singleton retriever (initialised once per process)
_retriever = None


def get_retriever():
    """Lazy singleton accessor for the vector-store retriever."""
    global _retriever
    if _retriever is None:
        _retriever = _build_retriever()
    return _retriever


# ---------------------------------------------------------------------------
# Node: retrieve
# ---------------------------------------------------------------------------


def retrieve(state: AgentState) -> Dict[str, Any]:
    """
    Retrieval Node — fetches candidate documents from the vector store.

    Queries the ChromaDB vector store using the current ``state["question"]``
    and returns raw ``Document`` objects.  Increments ``loop_step`` to track
    the depth of the Retrieve → Grade → Rewrite cycle.

    Parameters
    ----------
    state : AgentState
        Current graph state.

    Returns
    -------
    dict
        Partial state update containing:
        - ``documents``: List of retrieved Document objects.
        - ``loop_step``: Incremented iteration counter.
        - ``error``: Error message if retrieval fails (else None).
    """
    logger.info(
        "NODE:retrieve | question='%s' | loop_step=%d",
        state["question"],
        state["loop_step"],
    )

    try:
        retriever = get_retriever()
        docs: List[Document] = retriever.invoke(state["question"])
        logger.info("NODE:retrieve | retrieved %d document(s)", len(docs))
        return {
            "documents": docs,
            "loop_step": state["loop_step"] + 1,
            "error": None,
        }
    except Exception as exc:  # pylint: disable=broad-except
        logger.error("NODE:retrieve | exception: %s", exc, exc_info=True)
        return {
            "documents": [],
            "loop_step": state["loop_step"] + 1,
            "error": f"Retrieval failure: {exc}",
        }


# ---------------------------------------------------------------------------
# Node: grade_documents
# ---------------------------------------------------------------------------


def grade_documents(state: AgentState) -> Dict[str, Any]:
    """
    Grader Node — evaluates the relevance of each retrieved document.

    Invokes the ``grader_chain`` (LLM with structured output) for each
    document in ``state["documents"]``. Computes the fraction of relevant
    documents and writes a routing signal to ``relevance_decision``.

    Decision logic
    --------------
    - If ``relevant_fraction >= RELEVANCE_THRESHOLD``, set
      ``relevance_decision = "generate"`` → proceed to synthesis.
    - If ``relevant_fraction < RELEVANCE_THRESHOLD`` AND
      ``loop_step < MAX_RETRIEVE_ITERATIONS``, set
      ``relevance_decision = "transform_query"`` → rewrite and retry.
    - If ``loop_step >= MAX_RETRIEVE_ITERATIONS``, force
      ``relevance_decision = "generate"`` regardless of quality (safety
      circuit-breaker).

    Parameters
    ----------
    state : AgentState
        Current graph state. Must contain non-empty ``documents``.

    Returns
    -------
    dict
        Partial state update containing:
        - ``graded_documents``: List of GradedDocument dicts.
        - ``relevance_decision``: Routing signal for conditional edge.
    """
    logger.info(
        "NODE:grade_documents | grading %d document(s) | loop_step=%d",
        len(state["documents"]),
        state["loop_step"],
    )

    graded: List[GradedDocument] = []

    for doc in state["documents"]:
        try:
            grade: RelevanceGrade = grader_chain.invoke(
                {"question": state["question"], "document": doc.page_content}
            )
            relevance = "relevant" if grade.binary_score.lower() == "yes" else "irrelevant"
            graded.append(
                GradedDocument(
                    document=doc,
                    relevance=relevance,
                    score=grade.confidence if relevance == "relevant" else 1.0 - grade.confidence,
                )
            )
            logger.debug(
                "  doc_id=%s | verdict=%s | confidence=%.3f | rationale=%s",
                doc.metadata.get("source", "unknown"),
                relevance,
                grade.confidence,
                grade.rationale,
            )
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning("  Grading failed for one document: %s", exc)
            # Treat grading failure as irrelevant (conservative)
            graded.append(
                GradedDocument(document=doc, relevance="irrelevant", score=0.0)
            )

    # Compute relevance fraction
    n_relevant = sum(1 for g in graded if g["relevance"] == "relevant")
    relevant_fraction = n_relevant / len(graded) if graded else 0.0
    logger.info(
        "NODE:grade_documents | relevant=%d/%d (%.0f%%)",
        n_relevant,
        len(graded),
        relevant_fraction * 100,
    )

    # Safety circuit-breaker: force generation if max iterations reached
    if state["loop_step"] >= MAX_RETRIEVE_ITERATIONS:
        logger.warning(
            "NODE:grade_documents | MAX_RETRIEVE_ITERATIONS (%d) reached — "
            "forcing generation.",
            MAX_RETRIEVE_ITERATIONS,
        )
        decision = "generate"
    elif relevant_fraction >= RELEVANCE_THRESHOLD:
        decision = "generate"
    else:
        decision = "transform_query"

    logger.info("NODE:grade_documents | routing decision → '%s'", decision)
    return {
        "graded_documents": graded,
        "relevance_decision": decision,
    }


# ---------------------------------------------------------------------------
# Node: transform_query
# ---------------------------------------------------------------------------


def transform_query(state: AgentState) -> Dict[str, Any]:
    """
    Query Transformation Node — rewrites the current query for better retrieval.

    When the Grader determines that the retrieved corpus is of insufficient
    quality, this node leverages an LLM with structured output to produce an
    academically enriched reformulation of the query, targeting more specific
    vocabulary from the GCN / EEG domain.

    Parameters
    ----------
    state : AgentState
        Current graph state. Reads ``question`` and ``original_question``.

    Returns
    -------
    dict
        Partial state update containing:
        - ``question``: The improved query string (replaces current question).
        - ``error``: Error message if transformation fails (else None).
    """
    logger.info(
        "NODE:transform_query | original='%s' | current='%s'",
        state["original_question"],
        state["question"],
    )

    try:
        result: TransformedQuery = transformer_chain.invoke(
            {
                "original_question": state["original_question"],
                "question": state["question"],
            }
        )
        logger.info(
            "NODE:transform_query | improved='%s' | reasoning='%s'",
            result.improved_query,
            result.reasoning,
        )
        return {"question": result.improved_query, "error": None}
    except Exception as exc:  # pylint: disable=broad-except
        logger.error("NODE:transform_query | exception: %s", exc, exc_info=True)
        # Fall back to the original question to prevent state corruption
        return {"question": state["original_question"], "error": f"Query transformation failure: {exc}"}


# ---------------------------------------------------------------------------
# Node: generate
# ---------------------------------------------------------------------------


def generate(state: AgentState) -> Dict[str, Any]:
    """
    Generator Node — synthesises a rigorous academic answer.

    Selects only the ``"relevant"`` documents from ``graded_documents`` as
    context for the LLM. Falls back to all raw ``documents`` if no graded
    documents are available (e.g., grader was bypassed due to circuit-breaker
    triggering on the first iteration).

    The synthesised answer is written to ``state["generation"]``.

    Parameters
    ----------
    state : AgentState
        Current graph state.

    Returns
    -------
    dict
        Partial state update containing:
        - ``generation``: The synthesised academic answer string.
        - ``error``: Error message if generation fails (else None).
    """
    logger.info("NODE:generate | composing synthesis...")

    # Select context: prefer graded-relevant documents, else fall back to raw
    if state.get("graded_documents"):
        context_docs = [
            gd["document"]
            for gd in state["graded_documents"]
            if gd["relevance"] == "relevant"
        ]
        if not context_docs:
            # All documents were graded irrelevant but circuit-breaker forced
            # generation — use all graded documents as a last resort
            logger.warning(
                "NODE:generate | no relevant documents; using full corpus as fallback."
            )
            context_docs = [gd["document"] for gd in state["graded_documents"]]
    else:
        context_docs = state.get("documents", [])

    # Format context with source metadata
    context_str = "\n\n---\n\n".join(
        f"[Source: {doc.metadata.get('title', 'Unknown')} "
        f"({doc.metadata.get('year', 'n.d.')})] \n{doc.page_content}"
        for doc in context_docs
    )

    logger.info(
        "NODE:generate | using %d context document(s)", len(context_docs)
    )

    try:
        answer: str = generator_chain.invoke(
            {"question": state["question"], "context": context_str}
        )
        logger.info(
            "NODE:generate | synthesis complete (%d chars)", len(answer)
        )
        return {"generation": answer, "error": None}
    except Exception as exc:  # pylint: disable=broad-except
        logger.error("NODE:generate | exception: %s", exc, exc_info=True)
        return {
            "generation": (
                "Generation failed due to an internal error. "
                "Please inspect the logs and retry."
            ),
            "error": f"Generation failure: {exc}",
        }
