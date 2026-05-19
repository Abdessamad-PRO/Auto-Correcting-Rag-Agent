/** Domain models exchanged with the FastAPI backend. */

export type PromptVariant = 'A' | 'B';
export type HumanAction = 'approve' | 'edit_answer' | 'revise_query';
export type DocOrigin = 'vector' | 'web';

export interface DocumentPreview {
  title?: string;
  year?: number | string;
  source?: string;
  snippet: string;
  score?: number;
  relevance?: 'relevant' | 'irrelevant' | null;
  origin?: DocOrigin;
}

export interface AgentRunRequest {
  question: string;
  prompt_variant?: PromptVariant;
  thread_id?: string;
}

export interface HumanResumeRequest {
  action: HumanAction;
  edited_answer?: string | null;
  new_question?: string | null;
  feedback?: string | null;
}

export interface AgentRunResponse {
  thread_id: string;
  question: string;
  plan?: string | null;
  final_answer?: string | null;
  generation?: string | null;
  needs_human_review: boolean;
  human_feedback?: string | null;
  loop_step: number;
  documents: DocumentPreview[];
  graded_documents: DocumentPreview[];
  web_results: DocumentPreview[];
  error?: string | null;
  interrupted: boolean;
  interrupt_payload?: Record<string, unknown> | null;
}

/* ---------- SSE event payloads --------------------------------------- */

export type SseEventName = 'meta' | 'update' | 'interrupt' | 'final' | 'error';

export interface SseMessage<T = unknown> {
  event: SseEventName;
  data: T;
}

export type TraceNodeName =
  | 'plan_research'
  | 'retrieve'
  | 'grade_documents'
  | 'transform_query'
  | 'web_search'
  | 'generate'
  | 'review_answer'
  | 'human_in_the_loop';

export interface TraceUpdate {
  node: TraceNodeName;
  plan?: string;
  loop_step?: number;
  docs?: DocumentPreview[];
  relevant?: number;
  total?: number;
  decision?: string;
  question?: string;
  web_results?: DocumentPreview[];
  generation?: string;
  needs_human_review?: boolean;
  feedback?: string;
  final_answer?: string;
  error?: string;
  /** Client-side timestamp for trace rendering. */
  ts?: string;
}

export interface InterruptEvent {
  thread_id: string;
  interrupt: {
    type?: string;
    question?: string;
    plan?: string;
    draft_answer?: string;
    review_feedback?: string;
    error?: string;
    actions?: HumanAction[];
  };
}

export interface FinalEvent {
  thread_id: string;
  final_answer?: string | null;
  error?: string | null;
}
