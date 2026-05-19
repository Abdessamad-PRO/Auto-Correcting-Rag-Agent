import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../../environments/environment';
import {
  AgentRunRequest,
  AgentRunResponse,
  HumanResumeRequest,
} from '../models/agent.model';

@Injectable({ providedIn: 'root' })
export class AgentApiService {
  private readonly http = inject(HttpClient);
  private readonly base = `${environment.apiBaseUrl}/api/agent`;

  run(req: AgentRunRequest): Observable<AgentRunResponse> {
    return this.http.post<AgentRunResponse>(`${this.base}/run`, req);
  }

  resume(threadId: string, body: HumanResumeRequest): Observable<AgentRunResponse> {
    return this.http.post<AgentRunResponse>(`${this.base}/resume/${threadId}`, body);
  }

  getState(threadId: string): Observable<AgentRunResponse> {
    return this.http.get<AgentRunResponse>(`${this.base}/state/${threadId}`);
  }

  /** Build the absolute SSE URL for the EventSource constructor. */
  streamUrl(question: string, variant: 'A' | 'B' = 'A', threadId?: string): string {
    const params = new URLSearchParams({
      question,
      prompt_variant: variant,
      ...(threadId ? { thread_id: threadId } : {}),
    });
    return `${this.base}/stream?${params.toString()}`;
  }

  resumeStreamUrl(threadId: string, payload: HumanResumeRequest): string {
    const params = new URLSearchParams({
      action: payload.action,
      ...(payload.edited_answer ? { edited_answer: payload.edited_answer } : {}),
      ...(payload.new_question ? { new_question: payload.new_question } : {}),
      ...(payload.feedback ? { feedback: payload.feedback } : {}),
    });
    return `${this.base}/resume/${threadId}/stream?${params.toString()}`;
  }
}
