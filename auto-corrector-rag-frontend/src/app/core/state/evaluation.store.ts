import { computed, inject, Injectable, signal } from '@angular/core';

import { EvaluationResponse, VariantScores } from '../models/evaluation.model';
import { EvaluationApiService } from '../services/evaluation-api.service';

interface VariantOutcome {
  variant: string;
  scores: VariantScores;
}

@Injectable({ providedIn: 'root' })
export class EvaluationStore {
  private readonly api = inject(EvaluationApiService);

  readonly query = signal<string>('');
  readonly busy = signal<boolean>(false);
  readonly error = signal<string | null>(null);
  readonly result = signal<EvaluationResponse | null>(null);

  readonly outcomes = computed<VariantOutcome[]>(() => {
    const r = this.result();
    if (!r) return [];
    return Object.entries(r.summary).map(([variant, scores]) => ({ variant, scores }));
  });

  readonly winner = computed(() => {
    const list = this.outcomes();
    if (!list.length) return null;
    return list.reduce((best, cur) =>
      cur.scores.overall > best.scores.overall ? cur : best,
    );
  });

  runEvaluation(question: string): void {
    const q = question.trim();
    if (!q) return;
    this.query.set(q);
    this.busy.set(true);
    this.error.set(null);
    this.result.set(null);

    this.api.evaluate({ questions: [q], variants: ['A', 'B'] }).subscribe({
      next: (resp) => { this.result.set(resp); this.busy.set(false); },
      error: (err) => { this.error.set(String(err?.message ?? err)); this.busy.set(false); },
    });
  }
}
