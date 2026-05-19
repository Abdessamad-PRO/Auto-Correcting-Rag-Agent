import { ChangeDetectionStrategy, Component, computed, inject } from '@angular/core';

import { AgentSessionStore } from '../../../core/state/agent-session.store';
import { TraceNodeName } from '../../../core/models/agent.model';

interface TraceStyle {
  icon: string;
  color: string;
  label: string;
}

const NODE_STYLE: Record<TraceNodeName, TraceStyle> = {
  plan_research: { icon: 'flag', color: 'text-secondary', label: 'Planner Node' },
  retrieve: { icon: 'arrow_forward', color: 'text-tertiary-container', label: 'Retriever Node' },
  grade_documents: { icon: 'rule', color: 'text-tertiary-container', label: 'Grader Node' },
  transform_query: { icon: 'edit', color: 'text-secondary', label: 'Query Transformer' },
  web_search: { icon: 'travel_explore', color: 'text-tertiary-fixed-dim', label: 'Web Search Tool' },
  generate: { icon: 'auto_awesome', color: 'text-primary', label: 'Generator Node' },
  review_answer: { icon: 'fact_check', color: 'text-error', label: 'Reviewer Node' },
  human_in_the_loop: { icon: 'pan_tool', color: 'text-error', label: 'Human-in-the-loop' },
};

@Component({
  selector: 'app-live-trace',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <aside
      class="w-80 flex-shrink-0 bg-surface border-l border-outline-variant flex flex-col
             overflow-hidden hidden lg:flex relative z-10 scanline"
    >
      <div
        class="p-panel-padding border-b border-outline-variant flex items-center justify-between
               bg-surface-container-high"
      >
        <h3 class="font-label-caps text-label-caps text-primary uppercase tracking-widest">
          Live Agent Trace
        </h3>
        @if (session.isStreaming()) {
          <span class="flex h-2 w-2 relative">
            <span class="animate-ping absolute inline-flex h-full w-full rounded-full
                         bg-tertiary-container opacity-75"></span>
            <span class="relative inline-flex rounded-full h-2 w-2 bg-tertiary-container"></span>
          </span>
        } @else if (session.isPaused()) {
          <span class="w-2 h-2 rounded-full bg-error"></span>
        } @else {
          <span class="w-2 h-2 rounded-full bg-outline"></span>
        }
      </div>

      <div
        class="flex-1 overflow-y-auto cyber-scroll p-panel-padding font-technical-data
               text-technical-data flex flex-col gap-3"
      >
        @if (session.trace().length === 0 && !session.isStreaming()) {
          <p class="text-on-surface-variant text-center mt-8 font-body-md">
            Trace will appear here once a session starts.
          </p>
        }

        @for (entry of session.trace(); track $index) {
          @let s = style(entry.node);
          <div class="flex flex-col gap-1">
            <div class="flex items-center gap-2 text-on-surface-variant">
              <span class="material-symbols-outlined text-sm" [class]="s.color">{{ s.icon }}</span>
              <span>
                [{{ entry.ts }}]
                <span [class]="s.color">{{ s.label }}</span>
              </span>
            </div>
            <div class="pl-6 text-on-surface">
              {{ describe(entry) }}
            </div>
            @if (entry.error) {
              <div class="ml-6 mt-1 text-error border border-error-container bg-on-error/5 p-1 text-xs">
                {{ entry.error }}
              </div>
            }
          </div>
        }

        @if (session.isStreaming()) {
          <div class="flex items-center gap-2 text-tertiary-container mt-2 pl-6">
            <span class="w-2 h-2 bg-tertiary-container rounded-full animate-pulse"></span>
            <span>Streaming…</span>
          </div>
        }
      </div>

      <div class="border-t border-outline-variant p-panel-padding text-on-surface-variant
                  text-technical-data font-technical-data flex gap-3 flex-wrap">
        <span>Loop: <span class="text-on-surface">{{ session.loopStep() }}</span></span>
        <span>Relevant: <span class="text-on-surface">{{ session.relevantCount() }}/{{ session.totalGraded() }}</span></span>
        @if (session.relevanceDecision(); as d) {
          <span>Route: <span class="text-tertiary-container">{{ d }}</span></span>
        }
      </div>
    </aside>
  `,
})
export class LiveTraceComponent {
  protected readonly session = inject(AgentSessionStore);

  protected style(node: string): TraceStyle {
    return (NODE_STYLE as Record<string, TraceStyle>)[node] ?? {
      icon: 'subdirectory_arrow_right',
      color: 'text-on-surface-variant',
      label: node,
    };
  }

  protected describe(u: any): string {
    switch (u.node) {
      case 'plan_research':
        return (u.plan ?? 'Building research plan…').toString().slice(0, 180);
      case 'retrieve':
        return `Retrieved ${u.docs?.length ?? 0} document(s) (loop_step → ${u.loop_step})`;
      case 'grade_documents':
        return `Relevance ${u.relevant ?? 0}/${u.total ?? 0} — route → ${u.decision ?? '?'}`;
      case 'transform_query':
        return `New query: ${u.question ?? ''}`;
      case 'web_search':
        return `Web search returned ${u.web_results?.length ?? 0} result(s)`;
      case 'generate':
        return `Generated ${u.generation?.length ?? 0} characters`;
      case 'review_answer':
        return u.needs_human_review
          ? `Needs human review — ${u.feedback ?? ''}`
          : `Review passed${u.feedback ? ' — ' + u.feedback : ''}`;
      case 'human_in_the_loop':
        return u.final_answer ? 'Approved by reviewer' : 'Awaiting human action…';
      default:
        return JSON.stringify(u);
    }
  }
}
