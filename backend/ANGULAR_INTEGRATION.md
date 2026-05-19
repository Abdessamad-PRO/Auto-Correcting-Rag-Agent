# Angular ↔ FastAPI Integration

CORS is pre-configured for `http://localhost:4200`. Adjust via `CORS_ORIGINS`
in `.env` for production hosts.

## Suggested Angular service

```ts
// src/app/services/agent.service.ts
import { HttpClient } from '@angular/common/http';
import { Injectable, NgZone } from '@angular/core';
import { Observable } from 'rxjs';

const API = 'http://localhost:8000/api';

export interface AgentRunRequest {
  question: string;
  prompt_variant?: 'A' | 'B';
  thread_id?: string;
}

export interface DocumentPreview {
  title?: string; year?: any; source?: string;
  snippet: string; score?: number; relevance?: string;
  origin?: 'vector' | 'web';
}

export interface AgentRunResponse {
  thread_id: string;
  question: string;
  plan?: string;
  final_answer?: string;
  generation?: string;
  needs_human_review: boolean;
  human_feedback?: string;
  loop_step: number;
  documents: DocumentPreview[];
  graded_documents: DocumentPreview[];
  web_results: DocumentPreview[];
  error?: string;
  interrupted: boolean;
  interrupt_payload?: any;
}

@Injectable({ providedIn: 'root' })
export class AgentService {
  constructor(private http: HttpClient, private zone: NgZone) {}

  health() { return this.http.get(`${API}/health`); }

  run(req: AgentRunRequest) {
    return this.http.post<AgentRunResponse>(`${API}/agent/run`, req);
  }

  resume(threadId: string, body: any) {
    return this.http.post<AgentRunResponse>(`${API}/agent/resume/${threadId}`, body);
  }

  /** Live stream of node updates via Server-Sent Events. */
  stream(question: string, variant: 'A' | 'B' = 'A'): Observable<{event: string; data: any}> {
    return new Observable(sub => {
      const url = `${API}/agent/stream?question=${encodeURIComponent(question)}&prompt_variant=${variant}`;
      const es = new EventSource(url);
      const forward = (event: string) => (e: MessageEvent) =>
        this.zone.run(() => sub.next({ event, data: JSON.parse(e.data) }));

      es.addEventListener('meta',      forward('meta'));
      es.addEventListener('update',    forward('update'));
      es.addEventListener('interrupt', forward('interrupt'));
      es.addEventListener('final',     (e: MessageEvent) => {
        this.zone.run(() => { sub.next({ event: 'final', data: JSON.parse(e.data) }); sub.complete(); });
      });
      es.onerror = (err) => this.zone.run(() => sub.error(err));

      return () => es.close();
    });
  }

  ingestUpload(files: File[]) {
    const fd = new FormData();
    files.forEach(f => fd.append('files', f));
    return this.http.post(`${API}/ingest/upload`, fd);
  }

  evaluate(questions: string[], variants: ('A'|'B')[] = ['A','B']) {
    return this.http.post(`${API}/evaluate`, { questions, variants });
  }
}
```

## SSE event sequence

```
event: meta        → { thread_id }
event: update      → { node: 'plan_research', plan }
event: update      → { node: 'retrieve', loop_step, docs }
event: update      → { node: 'grade_documents', relevant, total, decision }
event: update      → { node: 'web_search', web_results }       // only if escalated
event: update      → { node: 'generate', generation }
event: update      → { node: 'review_answer', needs_human_review, feedback }
event: interrupt   → { thread_id, interrupt: { ... actions: [...] } }   // optional
event: final       → { thread_id, final_answer, error }
```

To resume after `interrupt`, POST to `/api/agent/resume/{thread_id}` with:

```json
{
  "action": "approve" | "edit_answer" | "revise_query",
  "edited_answer": "...optional...",
  "new_question":  "...optional...",
  "feedback":      "...optional..."
}
```
