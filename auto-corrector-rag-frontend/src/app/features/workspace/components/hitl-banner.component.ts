import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';

import { AgentSessionStore } from '../../../core/state/agent-session.store';
import { HumanAction } from '../../../core/models/agent.model';

@Component({
  selector: 'app-hitl-banner',
  standalone: true,
  imports: [FormsModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    @if (session.isPaused() && session.interrupt(); as intr) {
      <div
        class="bg-surface border-b border-outline-variant p-4
               flex flex-col gap-3 border-l-4 border-l-error"
      >
        <div class="flex items-center justify-between gap-3">
          <div class="flex items-center gap-3">
            <span class="material-symbols-outlined text-error">warning</span>
            <div>
              <h3 class="font-technical-data text-technical-data text-error font-bold uppercase">
                Human Input Required
              </h3>
              <p class="font-body-md text-on-surface-variant text-sm">
                {{ intr.review_feedback ?? 'Agent paused for human validation.' }}
              </p>
            </div>
          </div>
          <div class="flex gap-2 flex-wrap">
            <button type="button" class="hitl-btn" (click)="setAction('revise_query')">
              Edit Prompt
            </button>
            <button type="button" class="hitl-btn" (click)="setAction('edit_answer')">
              Edit Answer
            </button>
            <button
              type="button"
              class="hitl-btn primary"
              (click)="approve()"
              [disabled]="session.isStreaming()"
            >
              Approve & Resume
            </button>
          </div>
        </div>

        @if (action() !== 'approve') {
          <div class="grid grid-cols-1 md:grid-cols-12 gap-3 items-start">
            @if (action() === 'edit_answer') {
              <textarea
                class="md:col-span-9 bg-surface-container-low border border-outline-variant
                       text-on-surface font-technical-data text-technical-data p-2 h-24
                       focus:border-tertiary-fixed-dim focus:outline-none focus:ring-0"
                placeholder="Edited answer..."
                [(ngModel)]="editedAnswer"
              ></textarea>
            }
            @if (action() === 'revise_query') {
              <input
                type="text"
                class="md:col-span-9 bg-surface-container-low border border-outline-variant
                       text-on-surface font-technical-data text-technical-data p-2
                       focus:border-tertiary-fixed-dim focus:outline-none focus:ring-0"
                placeholder="Revised question..."
                [(ngModel)]="newQuestion"
              />
            }
            <input
              type="text"
              class="md:col-span-3 bg-surface-container-low border border-outline-variant
                     text-on-surface font-technical-data text-technical-data p-2
                     focus:border-tertiary-fixed-dim focus:outline-none focus:ring-0"
              placeholder="Feedback (optional)"
              [(ngModel)]="feedback"
            />
            <div class="md:col-span-12 flex justify-end gap-2">
              <button type="button" class="hitl-btn" (click)="setAction('approve')">Cancel</button>
              <button type="button" class="hitl-btn primary" (click)="submit()">Submit</button>
            </div>
          </div>
        }
      </div>
    }
  `,
  styles: [`
    .hitl-btn {
      padding: 4px 12px;
      border: 1px solid var(--color-outline-variant);
      color: var(--color-on-surface-variant);
      font-family: var(--font-label-caps);
      font-size: 12px;
      line-height: 16px;
      letter-spacing: 0.08em;
      font-weight: 600;
      transition: background-color 150ms, color 150ms;
      text-transform: uppercase;
    }
    .hitl-btn:hover {
      color: var(--color-primary);
      background: var(--color-surface-variant);
    }
    .hitl-btn.primary {
      background: var(--color-surface-variant);
      color: var(--color-primary);
    }
    .hitl-btn.primary:hover { background: var(--color-primary); color: var(--color-surface-dim); }
    .hitl-btn:disabled { opacity: 0.5; cursor: not-allowed; }
  `],
})
export class HitlBannerComponent {
  protected readonly session = inject(AgentSessionStore);
  protected readonly action = signal<HumanAction>('approve');
  protected editedAnswer = '';
  protected newQuestion = '';
  protected feedback = '';

  protected setAction(a: HumanAction): void {
    this.action.set(a);
    if (a === 'edit_answer') {
      this.editedAnswer = this.session.generation() ?? '';
    }
    if (a === 'revise_query') {
      this.newQuestion = this.session.question();
    }
  }

  protected approve(): void {
    this.session.resume({ action: 'approve', feedback: this.feedback || null });
    this.feedback = '';
  }

  protected submit(): void {
    const a = this.action();
    this.session.resume({
      action: a,
      edited_answer: a === 'edit_answer' ? this.editedAnswer : null,
      new_question: a === 'revise_query' ? this.newQuestion : null,
      feedback: this.feedback || null,
    });
    this.editedAnswer = '';
    this.newQuestion = '';
    this.feedback = '';
    this.action.set('approve');
  }
}
