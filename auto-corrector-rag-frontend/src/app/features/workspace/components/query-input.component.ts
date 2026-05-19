import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';

import { AgentSessionStore } from '../../../core/state/agent-session.store';
import { PromptVariant } from '../../../core/models/agent.model';

@Component({
  selector: 'app-query-input',
  standalone: true,
  imports: [FormsModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="p-panel-padding bg-surface-container-low border-t border-outline-variant">
      <div class="max-w-4xl mx-auto flex flex-col gap-2">
        <div class="flex items-center gap-3 text-on-surface-variant font-label-caps text-label-caps uppercase">
          <span>Prompt Variant</span>
          <button
            type="button"
            class="variant-pill"
            [class.active]="variant() === 'A'"
            (click)="variant.set('A')"
          >A · Narrative</button>
          <button
            type="button"
            class="variant-pill"
            [class.active]="variant() === 'B'"
            (click)="variant.set('B')"
          >B · Structured</button>
          @if (session.isStreaming()) {
            <button
              type="button"
              class="ml-auto variant-pill danger"
              (click)="session.cancel()"
            >Cancel</button>
          }
        </div>

        <div class="relative flex items-center">
          <span
            class="material-symbols-outlined absolute left-3 text-on-surface-variant"
          >keyboard_double_arrow_right</span>
          <input
            type="text"
            class="w-full bg-transparent border-0 border-b border-outline-variant
                   focus:border-tertiary-container focus:ring-0 font-technical-data
                   text-technical-data text-primary pl-10 pr-28 py-3
                   placeholder-on-surface-variant outline-none"
            placeholder="Direct the agent or ask a follow-up question..."
            [(ngModel)]="query"
            (keydown.enter)="submit()"
            [disabled]="session.isStreaming() || session.isPaused()"
          />
          <button
            type="button"
            class="absolute right-2 top-1/2 -translate-y-1/2 px-3 py-1
                   bg-surface-variant border border-outline-variant text-primary
                   font-label-caps text-label-caps hover:bg-primary
                   hover:text-surface-dim transition-colors disabled:opacity-40"
            [disabled]="!query.trim() || session.isStreaming() || session.isPaused()"
            (click)="submit()"
          >
            Execute
          </button>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .variant-pill {
      padding: 4px 10px;
      border: 1px solid var(--color-outline-variant);
      color: var(--color-on-surface-variant);
      font-family: var(--font-label-caps);
      font-size: 12px;
      letter-spacing: 0.08em;
      transition: all 150ms;
    }
    .variant-pill:hover { color: var(--color-primary); }
    .variant-pill.active {
      background: var(--color-surface-variant);
      color: var(--color-primary);
      border-color: var(--color-primary);
    }
    .variant-pill.danger {
      color: var(--color-error);
      border-color: var(--color-error);
    }
  `],
})
export class QueryInputComponent {
  protected readonly session = inject(AgentSessionStore);
  protected readonly variant = signal<PromptVariant>('A');
  protected query = '';

  protected submit(): void {
    const q = this.query.trim();
    if (!q) return;
    this.session.run(q, this.variant());
    this.query = '';
  }
}
