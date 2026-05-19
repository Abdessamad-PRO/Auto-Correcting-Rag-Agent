import { PromptVariant } from './agent.model';

export interface EvaluationRequest {
  questions: string[];
  variants?: PromptVariant[];
}

export interface VariantScores {
  answer_relevance: number;
  groundedness: number;
  overall: number;
}

export interface EvaluationResponse {
  summary: Record<string, VariantScores>;
}
