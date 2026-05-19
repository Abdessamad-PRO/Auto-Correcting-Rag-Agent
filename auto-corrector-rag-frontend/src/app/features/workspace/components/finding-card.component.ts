import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { DecimalPipe } from '@angular/common';

import { AgentSessionStore } from '../../../core/state/agent-session.store';

@Component({
  selector: 'app-finding-card',
  standalone: true,
  imports: [DecimalPipe],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    @if (session.hasAnswer()) {
      <article
        class="bg-surface border border-outline-variant p-6 flex flex-col gap-4
               max-w-4xl shadow-brutal"
      >
        <div class="flex items-center gap-2 border-b border-outline-variant pb-2">
          <span class="material-symbols-outlined text-tertiary-container text-sm">
            manage_search
          </span>
          <span class="font-label-caps text-label-caps text-tertiary-container uppercase">
            Synthesis Output
          </span>
          @if (session.finalAnswer()) {
            <span class="ml-auto font-label-caps text-label-caps text-tertiary-fixed-dim uppercase">
              Approved
            </span>
          }
        </div>

        <pre
          class="font-body-lg text-body-lg text-on-surface leading-relaxed whitespace-pre-wrap"
        >{{ session.answer() }}</pre>

        @if (session.citations().length > 0) {
          <div class="border-l-2 border-outline pl-4 mt-2 flex flex-col gap-2">
            @for (c of session.citations(); track c.id) {
              <div class="flex items-center gap-2 flex-wrap">
                <span class="font-technical-data text-technical-data text-on-surface-variant">
                  [{{ c.id }}] {{ c.label }}
                </span>
                @if (c.origin) {
                  <span
                    class="px-1.5 py-0.5 text-xs font-technical-data border border-outline-variant uppercase"
                    [class.bg-tertiary-container]="c.origin === 'web'"
                    [class.text-on-tertiary-container]="c.origin === 'web'"
                    [class.bg-surface-variant]="c.origin !== 'web'"
                    [class.text-on-surface-variant]="c.origin !== 'web'"
                  >
                    {{ c.origin }}
                  </span>
                }
                @if (c.confidence !== undefined) {
                  <span
                    class="bg-surface-variant text-on-surface-variant px-1.5 py-0.5
                           text-xs font-technical-data border border-outline-variant"
                  >
                    Confidence: {{ c.confidence | number: '1.2-2' }}
                  </span>
                }
              </div>
            }
          </div>
        }

        @if (session.humanFeedback(); as fb) {
          <div class="border-t border-outline-variant pt-3 text-on-surface-variant font-technical-data text-technical-data">
            <span class="font-label-caps text-label-caps uppercase mr-2">Reviewer:</span>
            {{ fb }}
          </div>
        }
      </article>
    }
  `,
})
export class FindingCardComponent {
  protected readonly session = inject(AgentSessionStore);
}
