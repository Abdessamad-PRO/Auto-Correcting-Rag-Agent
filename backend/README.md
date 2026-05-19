# RAG Agent — FastAPI Backend

Refactored, layered backend for the **Auto-Correcting Academic Research Agent**.

## Stack

- **FastAPI** (async, SSE streaming for live agent traces)
- **LangGraph** orchestration with auto-correcting retrieval loop
- **Multi-provider LLM** (Gemini / OpenAI / Grok — auto-detected from `.env`)
- **ChromaDB** vector store
- **DuckDuckGo / Tavily** web search tool (agent can think *and* search the web)
- **uv** for dependency management

## Architecture

```
src/rag_agent/
├── main.py                 # FastAPI entry point
├── core/                   # Config, logging, provider factories
├── models/                 # Pydantic DTOs + LangGraph TypedDict state
├── repositories/           # Vector store + document repositories
├── services/               # Business logic
│   ├── tools/              # Web search, vector search tools
│   ├── prompts.py          # Prompt templates
│   ├── chains.py           # LLM chain factories
│   ├── nodes.py            # LangGraph node functions
│   ├── workflow.py         # Graph assembly
│   ├── agent_service.py    # Orchestrator (run, resume, stream)
│   ├── ingestion_service.py
│   └── evaluation_service.py
└── controllers/            # HTTP routers
    ├── agent_controller.py
    ├── ingestion_controller.py
    ├── evaluation_controller.py
    └── health_controller.py
```

## Quick start

```bash
# 1. Install uv if missing:   pipx install uv   (or)   pip install uv
cd backend
cp .env.example .env
# fill GEMINI_API_KEY or OPENAI_API_KEY or GROK_API_KEY

uv sync                                 # install deps
uv run rag-ingest ./papers              # ingest a PDF folder (one-off)
uv run rag-api                          # start API on :8000
# OpenAPI docs:   http://localhost:8000/docs
```

## Key endpoints (consumed by the Angular UI)

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/health` | Liveness probe + detected LLM provider |
| `POST` | `/api/agent/run` | Run agent synchronously (returns full final state) |
| `GET` | `/api/agent/stream` | **SSE stream** of every node update (real-time trace) |
| `POST` | `/api/agent/resume/{thread_id}` | Resume after human-in-the-loop interrupt |
| `GET` | `/api/agent/state/{thread_id}` | Inspect a running session |
| `POST` | `/api/ingest/pdfs` | Ingest a directory of PDFs |
| `POST` | `/api/ingest/upload` | Upload PDF(s) and ingest |
| `POST` | `/api/evaluate` | A/B evaluation across prompt variants |

All endpoints return JSON and CORS is preconfigured for `http://localhost:4200`.

## Human-in-the-loop

`/api/agent/stream` emits SSE events. When the reviewer demands human input, an
`interrupt` event is emitted carrying a `thread_id`. The Angular client posts to
`/api/agent/resume/{thread_id}` with `{ action, edited_answer?, new_question?, feedback? }`
to continue.

## Web search

When vector retrieval is empty *or* the grader rejects the corpus on the final
iteration, the agent automatically falls back to a **web search node** (DuckDuckGo
by default, Tavily if `TAVILY_API_KEY` is set) and merges results into the context.
