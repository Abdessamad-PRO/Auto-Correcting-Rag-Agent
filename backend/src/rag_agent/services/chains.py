"""Lazy-instantiated LLM chains — one per logical role.

Each accessor caches its chain on first use; chains share the underlying
chat model returned by :func:`rag_agent.core.llm_factory.get_chat_model`.
"""

from __future__ import annotations

from functools import lru_cache

from langchain_core.output_parsers import StrOutputParser

from ..core.llm_factory import get_chat_model, get_structured_chat_model
from ..models.grading import (
    AnswerReview,
    RelevanceGrade,
    ResearchPlan,
    TransformedQuery,
)
from . import prompts


@lru_cache(maxsize=1)
def grader_chain():
    return prompts.grader_prompt | get_structured_chat_model(RelevanceGrade)


@lru_cache(maxsize=2)
def generator_chain(variant: str = "A"):
    v = (variant or "A").upper()
    tmpl = prompts.generator_prompt_b if v == "B" else prompts.generator_prompt_a
    return tmpl | get_chat_model() | StrOutputParser()


@lru_cache(maxsize=1)
def transformer_chain():
    return prompts.transformer_prompt | get_structured_chat_model(TransformedQuery)


@lru_cache(maxsize=1)
def planner_chain():
    return prompts.planner_prompt | get_structured_chat_model(ResearchPlan)


@lru_cache(maxsize=1)
def reviewer_chain():
    return prompts.reviewer_prompt | get_structured_chat_model(AnswerReview)
