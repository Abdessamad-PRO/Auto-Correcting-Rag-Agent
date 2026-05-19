# RAG OS — Angular Frontend

Cyber-brutalist **MVVM** Angular workspace for the Auto-Correcting Academic
Research Agent. Connects to the FastAPI backend in [`../backend`](../backend)
via REST + Server-Sent Events.

## Stack

- **Angular 21** standalone APIs, signals, control flow, deferrable views
- **Tailwind v4** CSS-first theme (no `tailwind.config.js`) — design tokens in `src/styles.css`
- **MVVM** — feature pages (View) delegate to signal-based stores (ViewModel)
  which call typed API services (Model)
- **SSE** for live agent traces (`EventSource` wrapped in an Observable)
- **SSR-safe** — every `EventSource` / `performance` call guards `isPlatformBrowser`
- **Dev proxy** forwards `/api/*` to `http://localhost:8000`, eliminating CORS

## Architecture (MVVM)

```
src/app/
├── core/                       ─── Model layer
│   ├── models/                     typed DTOs mirroring the FastAPI schemas
│   ├── services/                   HTTP / SSE clients
│   │   ├── agent-api.service.ts
│   │   ├── ingestion-api.service.ts
│   │   ├── evaluation-api.service.ts
│   │   ├── health-api.service.ts
│   │   └── sse.service.ts
│   └── state/                  ─── ViewModel layer (signal stores)
│       ├── agent-session.store.ts      workspace lifecycle (run/resume/stream)
│       ├── library.store.ts            ingestion pipeline + corpus list
│       ├── evaluation.store.ts         A/B prompt evaluation
│       └── system-status.store.ts      backend health polling
│
├── features/                   ─── View layer
│   ├── workspace/                  /workspace
│   │   ├── workspace.page.ts
│   │   └── components/
│   │       ├── hitl-banner.component.ts
│   │       ├── finding-card.component.ts
│   │       ├── live-trace.component.ts
│   │       └── query-input.component.ts
│   ├── library/                    /library
│   │   ├── library.page.ts
│   │   └── components/
│   │       ├── upload-zone.component.ts
│   │       ├── pipeline-tasks.component.ts
│   │       ├── corpus-table.component.ts
│   │       └── evaluation-console.component.ts
│   └── system-health/              /system
│       └── system-health.page.ts
│
└── shared/
    └── layout/                 ─── chrome (TopAppBar, SideNav, Footer, Shell)
```

**MVVM contract:** components consume signals/methods on a store and emit
intent. They never call HTTP directly, never own mutable side-effect state,
and never reach into other features' DOM.

## Design system

The dark cyber-brutalist palette is wired into Tailwind v4 via `@theme {}` in
[`src/styles.css`](src/styles.css). Every token from the design spec is a
first-class utility:

| Tokens | Examples |
|---|---|
| Colours | `bg-surface`, `text-tertiary-container`, `border-outline-variant`, `text-error` |
| Spacing | `p-margin-edge`, `gap-gutter`, `mb-stack-loose`, `gap-unit` |
| Typography | `font-headline-md` + `text-headline-md`, `font-technical-data` + `text-technical-data`, `font-label-caps` + `text-label-caps` |
| Effects | `.cyber-scroll` (terminal scrollbar), `.scanline` (CRT overlay), `.shadow-brutal` |

Material Symbols are loaded from Google Fonts and rendered with the
`material-symbols-outlined` class.

## Backend wiring

The frontend assumes the FastAPI backend (`uv run rag-api`) is listening on
`http://localhost:8000`. During development the Angular dev server proxies
all `/api/*` calls there via [`proxy.conf.json`](proxy.conf.json), so the
browser only ever talks to the Angular origin.

| Frontend service / store | Backend endpoint |
|---|---|
| `AgentApiService.run` | `POST /api/agent/run` |
| `AgentApiService.streamUrl` (SSE) | `GET  /api/agent/stream` |
| `AgentApiService.resume` | `POST /api/agent/resume/{thread_id}` |
| `AgentApiService.resumeStreamUrl` | `GET  /api/agent/resume/{thread_id}/stream` |
| `IngestionApiService.uploadFiles` | `POST /api/ingest/upload` |
| `EvaluationApiService.evaluate` | `POST /api/evaluate` |
| `HealthApiService.health` | `GET  /api/health` |

## SSE event flow

`AgentSessionStore.run()` opens an `EventSource`. The `SseService` translates
named events into `{ event, data }` records and the store fans them into
discrete signals consumed by the workspace components:

```
meta        → threadId
update      → trace[] + per-node signals (plan, documents, gradedDocuments, …)
interrupt   → isPaused = true, interrupt payload (HITL banner appears)
final       → finalAnswer, isStreaming = false
```

When `interrupt` fires, the user picks an action in the HITL banner:

- `approve` → resume the graph as-is
- `edit_answer` → submit a corrected answer (stops the loop)
- `revise_query` → submit a new question (re-enters retrieval)

The banner calls `AgentSessionStore.resume()` which opens a new resume SSE
stream and merges the rest of the run into the same `trace[]`.

## Routes

| Path | View | Purpose |
|---|---|---|
| `/workspace` | `WorkspacePage` | Live agent workspace — query, finding card, trace, HITL |
| `/library` | `LibraryPage` | Upload, ingestion pipeline, indexed corpus, A/B evaluation |
| `/system` | `SystemHealthPage` | Provider / model / vector-store / web-search readout |

Routes are lazy-loaded with `loadComponent()`, so the initial bundle is small.

## Development

```bash
cd auto-corrector-rag-frontend
npm install
npm start                  # http://localhost:4200 (proxies /api → :8000)
npm run build              # SSR-enabled production build
npm test                   # Vitest unit tests
```

Make sure the FastAPI backend is up before testing the workspace:

```bash
cd ../backend
uv run rag-api             # http://localhost:8000
```

## Tailwind v4 notes

This project uses the new Tailwind 4 CSS-first config. There is no
`tailwind.config.js`; design tokens live entirely inside the `@theme {}`
block of `src/styles.css`. Adding a new colour or spacing token = adding one
CSS variable. The PostCSS plugin is enabled via `.postcssrc.json`.
