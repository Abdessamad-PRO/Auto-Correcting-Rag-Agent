import { ChangeDetectionStrategy, Component, inject } from '@angular/core';

import { AgentSessionStore } from '../../core/state/agent-session.store';
import { FindingCardComponent } from './components/finding-card.component';
import { HitlBannerComponent } from './components/hitl-banner.component';
import { LiveTraceComponent } from './components/live-trace.component';
import { QueryInputComponent } from './components/query-input.component';

/**
 * Research Workspace — the View of the workspace ViewModel
 * ({@link AgentSessionStore}). The page is a thin composition of
 * presentational components; all behaviour lives in the store.
 */
@Component({
  selector: 'app-workspace-page',
  standalone: true,
  imports: [
    FindingCardComponent,
    HitlBannerComponent,
    LiveTraceComponent,
    QueryInputComponent,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="flex-1 flex overflow-hidden">
      <!-- Centre pane -->
      <section class="flex-1 flex flex-col bg-surface-container-lowest overflow-hidden relative">
        <app-hitl-banner />

        <div class="flex-1 overflow-y-auto cyber-scroll p-margin-edge flex flex-col gap-6">
          @if (!session.question()) {
            <!-- Empty state -->
            <div class="flex flex-col items-center justify-center gap-6 mt-16 max-w-3xl mx-auto text-center">
              <span class="material-symbols-outlined text-6xl text-tertiary-container opacity-60">
                psychology
              </span>
              <h2 class="font-headline-md text-headline-md text-primary leading-tight">
                Ask the agent anything about your indexed corpus.
              </h2>
              <p class="font-body-md text-on-surface-variant max-w-xl">
                Queries are decomposed by the planner, grounded against ChromaDB, and
                automatically corrected through query rewrites or live web search.
                Risky answers are paused for human review.
              </p>
            </div>
          } @else {
            <!-- Query header -->
            <div class="flex flex-col gap-2 max-w-3xl">
              <div class="flex items-center gap-3">
                <span class="font-label-caps text-label-caps text-on-surface-variant uppercase tracking-widest">
                  Query Initiated
                </span>
                @if (session.threadId(); as tid) {
                  <span class="font-technical-data text-technical-data text-on-surface-variant">
                    · thread {{ tid.slice(0, 8) }}
                  </span>
                }
                <span class="font-technical-data text-technical-data text-tertiary-fixed-dim ml-auto">
                  Variant {{ session.promptVariant() }}
                </span>
              </div>
              <h2 class="font-headline-md text-headline-md text-primary leading-tight">
                {{ session.question() }}
              </h2>
              @if (session.plan(); as plan) {
                <details class="mt-2 border border-outline-variant bg-surface p-3">
                  <summary class="font-label-caps text-label-caps text-on-surface-variant uppercase cursor-pointer">
                    Research Plan
                  </summary>
                  <pre class="mt-2 font-technical-data text-technical-data text-on-surface whitespace-pre-wrap">{{ plan }}</pre>
                </details>
              }
            </div>

            <!-- KPI strip -->
            <div class="flex flex-wrap gap-3 max-w-4xl">
              <div class="kpi">
                <span class="font-label-caps text-label-caps text-on-surface-variant uppercase">Loop</span>
                <span class="font-technical-data text-technical-data text-primary">{{ session.loopStep() }}</span>
              </div>
              <div class="kpi">
                <span class="font-label-caps text-label-caps text-on-surface-variant uppercase">Relevance</span>
                <span class="font-technical-data text-technical-data text-primary">
                  {{ session.relevantCount() }}/{{ session.totalGraded() }}
                  @if (session.totalGraded() > 0) {
                    <span class="text-tertiary-fixed-dim ml-1">({{ session.progress() }}%)</span>
                  }
                </span>
              </div>
              @if (session.relevanceDecision(); as d) {
                <div class="kpi">
                  <span class="font-label-caps text-label-caps text-on-surface-variant uppercase">Route</span>
                  <span class="font-technical-data text-technical-data text-tertiary-container">{{ d }}</span>
                </div>
              }
              @if (session.webResults().length > 0) {
                <div class="kpi">
                  <span class="font-label-caps text-label-caps text-on-surface-variant uppercase">Web hits</span>
                  <span class="font-technical-data text-technical-data text-tertiary-fixed-dim">
                    {{ session.webResults().length }}
                  </span>
                </div>
              }
            </div>

            <!-- Finding card -->
            <app-finding-card />

            <!-- Streaming pulse -->
            @if (session.isStreaming() && !session.hasAnswer()) {
              <div class="flex items-center gap-3 max-w-3xl mt-4 opacity-70">
                <div class="w-2 h-2 bg-tertiary-container rounded-full animate-pulse"></div>
                <span class="font-technical-data text-technical-data text-tertiary-container">
                  Agent is reasoning across the corpus…
                </span>
              </div>
            }

            <!-- Error -->
            @if (session.error(); as err) {
              <div class="max-w-3xl border border-error bg-error-container/20 p-3 text-error font-technical-data text-technical-data">
                <span class="font-label-caps text-label-caps uppercase mr-2">Error</span>{{ err }}
              </div>
            }
          }
        </div>

        <app-query-input />
      </section>

      <!-- Right pane: live trace -->
      <app-live-trace />
    </div>
  `,
  styles: [`
    .kpi {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 4px 10px;
      border: 1px solid var(--color-outline-variant);
      background: var(--color-surface);
    }
  `],
})
export class WorkspacePage {
  protected readonly session = inject(AgentSessionStore);
}
