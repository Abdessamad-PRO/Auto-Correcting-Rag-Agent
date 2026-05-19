import { ChangeDetectionStrategy, Component, computed, inject } from '@angular/core';

import { SystemStatusStore } from '../../core/state/system-status.store';

@Component({
  selector: 'app-status-footer',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <footer
      class="bg-surface-container-lowest text-tertiary fixed bottom-0 w-full h-8
             border-t border-outline-variant flex justify-between items-center
             px-4 py-1 z-50"
    >
      <div class="font-technical-data text-technical-data text-on-surface-variant flex gap-4 items-center">
        <span class="flex items-center gap-2">
          <span
            class="w-2 h-2 rounded-full"
            [class.bg-tertiary-container]="status.online()"
            [class.bg-error]="!status.online()"
          ></span>
          System: {{ status.online() ? 'Operational' : 'Offline' }}
        </span>
        <span class="hidden sm:inline">|</span>
        <span class="hidden sm:inline">
          LLM: <span class="text-on-surface">{{ provider() }}</span>
        </span>
        <span class="hidden md:inline">|</span>
        <span class="hidden md:inline">
          Model: <span class="text-on-surface">{{ status.health()?.model ?? '—' }}</span>
        </span>
        <span class="hidden md:inline">|</span>
        <span class="hidden md:inline text-tertiary-container">
          Latency: {{ status.latencyMs() ?? '—' }}ms
        </span>
        <span class="hidden lg:inline">|</span>
        <span class="hidden lg:inline">
          ChromaDB: <span class="text-on-surface">{{ status.health()?.chroma_collection ?? '—' }}</span>
        </span>
      </div>
      <div class="flex gap-4">
        <a
          href="http://localhost:8000/docs"
          target="_blank"
          rel="noopener"
          class="font-label-caps text-label-caps text-on-surface-variant
                 hover:text-on-surface transition-colors uppercase"
        >
          API Status
        </a>
        <a
          href="#"
          class="font-label-caps text-label-caps text-on-surface-variant
                 hover:text-on-surface transition-colors uppercase"
        >
          Help Desk
        </a>
      </div>
    </footer>
  `,
})
export class StatusFooterComponent {
  protected readonly status = inject(SystemStatusStore);
  protected readonly provider = computed(() => {
    const h = this.status.health();
    if (!h) return '—';
    return `${h.provider} / ${h.web_search_provider}`;
  });
}
