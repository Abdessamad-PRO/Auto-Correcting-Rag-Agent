import { ChangeDetectionStrategy, Component, inject } from '@angular/core';

import { SystemStatusStore } from '../../core/state/system-status.store';

@Component({
  selector: 'app-system-health-page',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <main class="flex-1 overflow-y-auto cyber-scroll p-margin-edge">
      <div class="max-w-4xl mx-auto flex flex-col gap-stack-loose">
        <header class="flex items-end justify-between">
          <div>
            <h2 class="font-headline-md text-headline-md text-primary">System Health</h2>
            <p class="font-technical-data text-technical-data text-on-surface-variant">
              Live readout of the backend services powering this workspace.
            </p>
          </div>
          <button
            type="button"
            class="px-3 py-1 border border-outline-variant text-on-surface-variant
                   hover:text-primary hover:bg-surface-variant font-label-caps text-label-caps uppercase"
            (click)="status.refresh()"
          >Refresh</button>
        </header>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-px bg-outline-variant">
          <div class="bg-surface p-gutter">
            <span class="font-label-caps text-label-caps text-on-surface-variant uppercase">
              Backend
            </span>
            <div class="font-headline-sm text-headline-sm mt-1 flex items-center gap-2"
                 [class.text-tertiary-container]="status.online()"
                 [class.text-error]="!status.online()">
              <span
                class="w-3 h-3 rounded-full"
                [class.bg-tertiary-container]="status.online()"
                [class.bg-error]="!status.online()"
              ></span>
              {{ status.online() ? 'Operational' : 'Offline' }}
            </div>
            <p class="font-technical-data text-technical-data text-on-surface-variant mt-2">
              Latency: {{ status.latencyMs() ?? '—' }} ms
            </p>
          </div>

          <div class="bg-surface p-gutter">
            <span class="font-label-caps text-label-caps text-on-surface-variant uppercase">
              LLM Provider
            </span>
            <div class="font-headline-sm text-headline-sm mt-1 text-primary">
              {{ status.health()?.provider ?? '—' }}
            </div>
            <p class="font-technical-data text-technical-data text-on-surface-variant mt-2">
              Model: <span class="text-on-surface">{{ status.health()?.model ?? '—' }}</span>
            </p>
          </div>

          <div class="bg-surface p-gutter">
            <span class="font-label-caps text-label-caps text-on-surface-variant uppercase">
              Vector Store
            </span>
            <div class="font-headline-sm text-headline-sm mt-1 text-primary">ChromaDB</div>
            <p class="font-technical-data text-technical-data text-on-surface-variant mt-2">
              Collection: <span class="text-on-surface">{{ status.health()?.chroma_collection ?? '—' }}</span>
            </p>
            <p class="font-technical-data text-technical-data text-on-surface-variant">
              Persist dir: <span class="text-on-surface">{{ status.health()?.chroma_persist_dir ?? '—' }}</span>
            </p>
          </div>

          <div class="bg-surface p-gutter">
            <span class="font-label-caps text-label-caps text-on-surface-variant uppercase">
              Web Search Tool
            </span>
            <div class="font-headline-sm text-headline-sm mt-1 text-primary">
              {{ status.health()?.web_search_provider ?? '—' }}
            </div>
            <p class="font-technical-data text-technical-data text-on-surface-variant mt-2">
              Fallback when the corpus is empty or exhausted on the final retrieval loop.
            </p>
          </div>
        </div>

        @if (status.error(); as err) {
          <div class="border border-error bg-error-container/20 p-3 text-error font-technical-data text-technical-data">
            <span class="font-label-caps text-label-caps uppercase mr-2">Error</span>{{ err }}
          </div>
        }
      </div>
    </main>
  `,
})
export class SystemHealthPage {
  protected readonly status = inject(SystemStatusStore);
}
