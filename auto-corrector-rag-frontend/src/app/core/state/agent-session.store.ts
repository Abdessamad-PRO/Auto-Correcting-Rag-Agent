import { computed, inject, Injectable, signal } from '@angular/core';
import { Subscription } from 'rxjs';

import {
  AgentRunResponse,
  DocumentPreview,
  FinalEvent,
  HumanResumeRequest,
  InterruptEvent,
  PromptVariant,
  TraceUpdate,
} from '../models/agent.model';
import { AgentApiService } from '../services/agent-api.service';
import { SseService } from '../services/sse.service';

/** Citation extracted from a generation for the finding-card view. */
export interface Citation {
  id: number;
  label: string;
  confidence?: number;
  origin?: 'vector' | 'web';
  source?: string;
}

/**
 * Workspace ViewModel — owns the entire lifecycle of an agent session:
 * streaming, intermediate state, HITL interrupt, and resume.
 *
 * Components consume the public signals and call the public methods;
 * they never touch HTTP or SSE directly.
 */
@Injectable({ providedIn: 'root' })
export class AgentSessionStore {
  private readonly api = inject(AgentApiService);
  private readonly sse = inject(SseService);

  /* ---------------------- Reactive state (signals) ------------------- */
  readonly threadId = signal<string | null>(null);
  readonly question = signal<string>('');
  readonly promptVariant = signal<PromptVariant>('A');
  readonly plan = signal<string | null>(null);
  readonly generation = signal<string | null>(null);
  readonly finalAnswer = signal<string | null>(null);

  readonly documents = signal<DocumentPreview[]>([]);
  readonly gradedDocuments = signal<DocumentPreview[]>([]);
  readonly webResults = signal<DocumentPreview[]>([]);
  readonly trace = signal<TraceUpdate[]>([]);

  readonly loopStep = signal<number>(0);
  readonly relevanceDecision = signal<string | null>(null);
  readonly relevantCount = signal<number>(0);
  readonly totalGraded = signal<number>(0);

  readonly isStreaming = signal<boolean>(false);
  readonly isPaused = signal<boolean>(false);
  readonly interrupt = signal<InterruptEvent['interrupt'] | null>(null);
  readonly humanFeedback = signal<string | null>(null);
  readonly error = signal<string | null>(null);

  /* ---------------------- Derived signals ---------------------------- */
  readonly hasSession = computed(() => this.threadId() !== null);
  readonly hasAnswer = computed(() => !!(this.finalAnswer() || this.generation()));
  readonly answer = computed(() => this.finalAnswer() ?? this.generation());

  readonly citations = computed<Citation[]>(() => {
    const all = [...this.gradedDocuments(), ...this.webResults()];
    return all
      .filter((d) => (d.relevance ?? 'relevant') === 'relevant')
      .slice(0, 8)
      .map((d, idx) => ({
        id: idx + 1,
        label: this.formatCitation(d),
        confidence: d.score,
        origin: d.origin,
        source: d.source,
      }));
  });

  readonly progress = computed(() => {
    const t = this.totalGraded();
    return t > 0 ? Math.round((this.relevantCount() / t) * 100) : 0;
  });

  /* ---------------------- Streaming subscription --------------------- */
  private streamSub?: Subscription;

  /** Kick off a new streaming research session. */
  run(question: string, variant: PromptVariant = 'A'): void {
    this.reset();
    this.question.set(question);
    this.promptVariant.set(variant);
    this.isStreaming.set(true);

    const url = this.api.streamUrl(question, variant);
    this.streamSub = this.sse.connect(url).subscribe({
      next: (msg) => this.handleEvent(msg.event, msg.data),
      error: (err) => {
        this.error.set(String(err));
        this.isStreaming.set(false);
      },
      complete: () => this.isStreaming.set(false),
    });
  }

  /** Resume after a human-in-the-loop interrupt. */
  resume(payload: HumanResumeRequest): void {
    const tid = this.threadId();
    if (!tid) return;
    this.isPaused.set(false);
    this.isStreaming.set(true);
    this.interrupt.set(null);

    const url = this.api.resumeStreamUrl(tid, payload);
    this.streamSub = this.sse.connect(url).subscribe({
      next: (msg) => this.handleEvent(msg.event, msg.data),
      error: (err) => {
        this.error.set(String(err));
        this.isStreaming.set(false);
      },
      complete: () => this.isStreaming.set(false),
    });
  }

  cancel(): void {
    this.streamSub?.unsubscribe();
    this.streamSub = undefined;
    this.isStreaming.set(false);
  }

  reset(): void {
    this.cancel();
    this.threadId.set(null);
    this.plan.set(null);
    this.generation.set(null);
    this.finalAnswer.set(null);
    this.documents.set([]);
    this.gradedDocuments.set([]);
    this.webResults.set([]);
    this.trace.set([]);
    this.loopStep.set(0);
    this.relevanceDecision.set(null);
    this.relevantCount.set(0);
    this.totalGraded.set(0);
    this.isPaused.set(false);
    this.interrupt.set(null);
    this.humanFeedback.set(null);
    this.error.set(null);
  }

  /** Replace state from a non-streaming sync response (e.g. after resume). */
  hydrate(resp: AgentRunResponse): void {
    this.threadId.set(resp.thread_id);
    this.question.set(resp.question);
    this.plan.set(resp.plan ?? null);
    this.generation.set(resp.generation ?? null);
    this.finalAnswer.set(resp.final_answer ?? null);
    this.documents.set(resp.documents ?? []);
    this.gradedDocuments.set(resp.graded_documents ?? []);
    this.webResults.set(resp.web_results ?? []);
    this.loopStep.set(resp.loop_step ?? 0);
    this.humanFeedback.set(resp.human_feedback ?? null);
    this.error.set(resp.error ?? null);
    this.isPaused.set(resp.interrupted);
  }

  /* ---------------------- Internal helpers --------------------------- */
  private handleEvent(name: string, data: unknown): void {
    switch (name) {
      case 'meta': {
        const d = data as { thread_id: string };
        if (d?.thread_id) this.threadId.set(d.thread_id);
        break;
      }
      case 'update': {
        this.applyTraceUpdate(data as TraceUpdate);
        break;
      }
      case 'interrupt': {
        const d = data as InterruptEvent;
        this.threadId.set(d.thread_id);
        this.interrupt.set(d.interrupt);
        this.isPaused.set(true);
        this.isStreaming.set(false);
        break;
      }
      case 'final': {
        const d = data as FinalEvent;
        if (d?.final_answer) this.finalAnswer.set(d.final_answer);
        if (d?.error) this.error.set(d.error);
        this.isStreaming.set(false);
        break;
      }
      case 'error': {
        this.error.set('SSE connection error');
        break;
      }
    }
  }

  private applyTraceUpdate(u: TraceUpdate): void {
    const ts = new Date().toLocaleTimeString('en-GB', { hour12: false });
    this.trace.update((prev) => [...prev, { ...u, ts }]);

    switch (u.node) {
      case 'plan_research':
        if (u.plan) this.plan.set(u.plan);
        break;
      case 'retrieve':
        if (u.docs) this.documents.set(u.docs);
        if (typeof u.loop_step === 'number') this.loopStep.set(u.loop_step);
        break;
      case 'grade_documents':
        if (typeof u.relevant === 'number') this.relevantCount.set(u.relevant);
        if (typeof u.total === 'number') this.totalGraded.set(u.total);
        if (u.decision) this.relevanceDecision.set(u.decision);
        break;
      case 'transform_query':
        if (u.question) this.question.set(u.question);
        break;
      case 'web_search':
        if (u.web_results) this.webResults.set(u.web_results);
        break;
      case 'generate':
        if (u.generation) this.generation.set(u.generation);
        break;
      case 'review_answer':
        if (u.feedback) this.humanFeedback.set(u.feedback);
        break;
      case 'human_in_the_loop':
        if (u.final_answer) this.finalAnswer.set(u.final_answer);
        break;
    }
    if (u.error) this.error.set(u.error);
  }

  private formatCitation(d: DocumentPreview): string {
    const title = d.title ?? d.source ?? 'Unknown source';
    const year = d.year ? ` (${d.year})` : '';
    return `${title}${year}`;
  }
}
