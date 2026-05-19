"""Agent HTTP controller.

Endpoints
---------
POST /api/agent/run                      Synchronous invocation.
GET  /api/agent/stream                   SSE stream of node updates.
POST /api/agent/resume/{thread_id}       Resume after human-in-the-loop.
GET  /api/agent/resume/{thread_id}/stream  SSE resume.
GET  /api/agent/state/{thread_id}        Inspect a session.
"""

from __future__ import annotations

import json
from typing import AsyncIterator

from fastapi import APIRouter, Depends
from sse_starlette.sse import EventSourceResponse

from ..models.schemas import (
    AgentRunRequest,
    AgentRunResponse,
    HumanResumeRequest,
)
from ..services.agent_service import AgentService, get_agent_service

router = APIRouter(prefix="/api/agent", tags=["agent"])


# ---------------------------------------------------------------------------
# Sync
# ---------------------------------------------------------------------------


@router.post("/run", response_model=AgentRunResponse)
def run_agent(
    payload: AgentRunRequest,
    service: AgentService = Depends(get_agent_service),
) -> AgentRunResponse:
    return service.run(
        payload.question,
        prompt_variant=payload.prompt_variant,
        thread_id=payload.thread_id,
    )


@router.post("/resume/{thread_id}", response_model=AgentRunResponse)
def resume_agent(
    thread_id: str,
    payload: HumanResumeRequest,
    service: AgentService = Depends(get_agent_service),
) -> AgentRunResponse:
    return service.resume(thread_id, payload)


@router.get("/state/{thread_id}", response_model=AgentRunResponse)
def get_state(
    thread_id: str,
    service: AgentService = Depends(get_agent_service),
) -> AgentRunResponse:
    return service.get_state(thread_id)


# ---------------------------------------------------------------------------
# SSE streaming (consumed by Angular EventSource)
# ---------------------------------------------------------------------------


async def _sse_pump(it: AsyncIterator[dict]) -> AsyncIterator[dict]:
    async for msg in it:
        yield {"event": msg["event"], "data": json.dumps(msg["data"], ensure_ascii=False)}


@router.get("/stream")
async def stream_agent(
    question: str,
    prompt_variant: str = "A",
    thread_id: str | None = None,
    service: AgentService = Depends(get_agent_service),
) -> EventSourceResponse:
    gen = service.stream(question, prompt_variant=prompt_variant, thread_id=thread_id)
    return EventSourceResponse(_sse_pump(gen))


@router.get("/resume/{thread_id}/stream")
async def stream_resume(
    thread_id: str,
    action: str = "approve",
    edited_answer: str | None = None,
    new_question: str | None = None,
    feedback: str | None = None,
    service: AgentService = Depends(get_agent_service),
) -> EventSourceResponse:
    payload = HumanResumeRequest(
        action=action,  # type: ignore[arg-type]
        edited_answer=edited_answer,
        new_question=new_question,
        feedback=feedback,
    )
    gen = service.stream_resume(thread_id, payload)
    return EventSourceResponse(_sse_pump(gen))
