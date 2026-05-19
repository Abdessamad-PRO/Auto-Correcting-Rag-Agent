import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { DecimalPipe } from '@angular/common';
import { FormsModule } from '@angular/forms';

import { EvaluationStore } from '../../../core/state/evaluation.store';

@Component({
  selector: 'app-evaluation-console',
  standalone: true,
  imports: [DecimalPipe, FormsModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="bg-surface flex flex-col h-full border-l border-outline-variant">
      <div
        class="p-gutter border-b border-outline-variant bg-surface-container-low
               flex justify-between items-center"
      >
        <h3
          class="font-label-caps text-label-caps text-on-surface-variant uppercase
                 tracking-widest flex items-center gap-2"
        >
          <span class="material-symbols-outlined text-sm">science</span>
          Retrieval Evaluation
        </h3>
        <span class="px-2 py-0.5 bg-surface-variant border border-outline-variant
                     font-technical-data text-[10px] text-on-surface uppercase">
          A/B Console
        </span>
      </div>

      <div class="p-gutter flex-1 overflow-y-auto cyber-scroll">
        <div class="mb-stack-loose">
          <label class="font-label-caps text-label-caps text-on-surface-variant block mb-2 uppercase">
            Test Query
          </label>
          <textarea
            class="w-full bg-transparent border-b border-outline-variant
                   focus:border-tertiary-fixed-dim text-on-surface
                   font-technical-data text-technical-data py-2 px-0
                   focus:outline-none resize-none h-20"
            placeholder="Enter evaluation query..."
            [(ngModel)]="query"
            (keydown.meta.enter)="run()"
            (keydown.control.enter)="run()"
          ></textarea>
          <div class="flex justify-end mt-2">
            <button
              type="button"
              class="py-1 px-4 border border-outline-variant text-on-surface
                     hover:bg-surface-variant transition-colors font-label-caps text-label-caps
                     uppercase disabled:opacity-40"
              (click)="run()"
              [disabled]="!query.trim() || store.busy()"
            >
              {{ store.busy() ? 'Running…' : 'Run Eval' }}
            </button>
          </div>
        </div>

        @if (store.error(); as err) {
          <div class="border border-error bg-error-container/20 p-2 text-error
                      font-technical-data text-technical-data mb-3">
            {{ err }}
          </div>
        }

        <div class="flex flex-col gap-stack-compact relative">
          <div class="absolute left-3 top-4 bottom-4 w-px bg-outline-variant z-0"></div>

          @if (store.outcomes().length === 0 && !store.busy()) {
            <p class="font-technical-data text-technical-data text-on-surface-variant pl-8">
              Run an evaluation to compare prompt variants side-by-side.
            </p>
          }

          @for (out of store.outcomes(); track out.variant) {
            <div class="relative z-10 pl-8 transition-opacity"
                 [class.opacity-100]="store.winner()?.variant === out.variant"
                 [class.opacity-70]="store.winner()?.variant !== out.variant">
              <div class="absolute left-0 top-1 w-6 h-px bg-outline-variant"></div>
              <div
                class="absolute left-[3px] top-[1px] w-1.5 h-1.5 rounded-full"
                [class.bg-tertiary-container]="store.winner()?.variant === out.variant"
                [class.bg-outline-variant]="store.winner()?.variant !== out.variant"
              ></div>

              <div class="border border-outline-variant bg-surface p-panel-padding">
                <div class="flex justify-between items-center mb-2 border-b border-outline-variant/50 pb-2">
                  <span
                    class="font-label-caps text-label-caps uppercase"
                    [class.text-primary]="store.winner()?.variant === out.variant"
                    [class.text-on-surface]="store.winner()?.variant !== out.variant"
                  >
                    Variant {{ out.variant }}
                    @if (store.winner()?.variant === out.variant) {
                      <span class="text-tertiary-container ml-1">· winner</span>
                    }
                  </span>
                  <span class="font-technical-data text-technical-data text-on-surface-variant">
                    Overall: {{ out.scores.overall | number: '1.2-2' }}
                  </span>
                </div>
                <div class="grid grid-cols-2 gap-2 font-technical-data text-technical-data">
                  <div>
                    <span class="text-on-surface-variant">Relevance:</span>
                    <span class="text-on-surface ml-1">{{ out.scores.answer_relevance | number: '1.2-2' }}</span>
                  </div>
                  <div>
                    <span class="text-on-surface-variant">Groundedness:</span>
                    <span class="text-on-surface ml-1">{{ out.scores.groundedness | number: '1.2-2' }}</span>
                  </div>
                </div>
                <div class="w-full h-1 bg-surface-container-highest overflow-hidden mt-3">
                  <div
                    class="h-full bg-tertiary-fixed-dim transition-all"
                    [style.width.%]="out.scores.overall * 100"
                  ></div>
                </div>
              </div>
            </div>
          }
        </div>
      </div>
    </div>
  `,
})
export class EvaluationConsoleComponent {
  protected readonly store = inject(EvaluationStore);
  protected query = '';

  protected run(): void {
    this.store.runEvaluation(this.query);
  }
}
