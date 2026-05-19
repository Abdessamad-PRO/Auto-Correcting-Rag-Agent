"""LLM-as-judge evaluation across prompt variants."""

from __future__ import annotations

from typing import Dict, List

from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from ..core.llm_factory import get_chat_model
from ..core.logging import get_logger
from ..models.schemas import EvaluationRequest, EvaluationResponse, VariantScores
from .agent_service import get_agent_service

logger = get_logger(__name__)


class _JudgeScore(BaseModel):
    answer_relevance: float = Field(ge=0.0, le=1.0)
    groundedness: float = Field(ge=0.0, le=1.0)
    overall: float = Field(ge=0.0, le=1.0)
    rationale: str = ""


_JUDGE_SYSTEM = """\
You are a strict evaluator for an agentic RAG system.
Score the answer on:
  - answer_relevance: does it address the question?
  - groundedness: are claims supported by the provided context?
Return scores in [0, 1]. Be conservative.\
"""

_JUDGE_HUMAN = """\
Question:
{question}

Context:
{context}

Answer:
{answer}\
"""


def _context_from_response(resp) -> str:
    docs: List[Document] = []
    # Reconstruct context from preview snippets — sufficient for the judge.
    pool = resp.graded_documents or []
    relevant = [d for d in pool if (d.relevance or "") == "relevant"] or pool
    for d in relevant:
        docs.append(
            Document(
                page_content=d.snippet,
                metadata={"title": d.title, "year": d.year, "source": d.source},
            )
        )
    return "\n\n---\n\n".join(
        f"[Source: {d.metadata.get('title', 'Unknown')} ({d.metadata.get('year', 'n.d.')})] "
        f"\n{d.page_content}"
        for d in docs
    )


class EvaluationService:
    def __init__(self) -> None:
        self._agent = get_agent_service()
        prompt = ChatPromptTemplate.from_messages(
            [("system", _JUDGE_SYSTEM), ("human", _JUDGE_HUMAN)]
        )
        self._judge = prompt | get_chat_model().with_structured_output(_JudgeScore)

    def evaluate(self, request: EvaluationRequest) -> EvaluationResponse:
        per_variant: Dict[str, List[_JudgeScore]] = {v: [] for v in request.variants}
        for q in request.questions:
            for variant in request.variants:
                logger.info("EVAL | variant=%s | q=%r", variant, q)
                resp = self._agent.run(q, prompt_variant=variant)
                # If the agent stopped on a HIL interrupt, auto-approve to finalise.
                if resp.interrupted:
                    from ..models.schemas import HumanResumeRequest

                    resp = self._agent.resume(
                        resp.thread_id, HumanResumeRequest(action="approve")
                    )
                answer = resp.final_answer or resp.generation or ""
                context = _context_from_response(resp)
                score: _JudgeScore = self._judge.invoke(
                    {"question": q, "context": context, "answer": answer}
                )
                per_variant[variant].append(score)

        def _avg(scores: List[_JudgeScore]) -> VariantScores:
            if not scores:
                return VariantScores(answer_relevance=0.0, groundedness=0.0, overall=0.0)
            n = len(scores)
            return VariantScores(
                answer_relevance=sum(s.answer_relevance for s in scores) / n,
                groundedness=sum(s.groundedness for s in scores) / n,
                overall=sum(s.overall for s in scores) / n,
            )

        return EvaluationResponse(summary={v: _avg(s) for v, s in per_variant.items()})


_evaluation_service: EvaluationService | None = None


def get_evaluation_service() -> EvaluationService:
    global _evaluation_service
    if _evaluation_service is None:
        _evaluation_service = EvaluationService()
    return _evaluation_service
