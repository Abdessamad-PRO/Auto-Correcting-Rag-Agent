import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';

import { LibraryStore } from '../../../core/state/library.store';

@Component({
  selector: 'app-corpus-table',
  standalone: true,
  imports: [FormsModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <section class="bg-surface p-0 flex-1 flex flex-col">
      <div
        class="p-gutter border-b border-outline-variant flex justify-between items-center
               bg-surface-container-low"
      >
        <h3 class="font-label-caps text-label-caps text-on-surface-variant uppercase tracking-widest">
          Indexed Corpus
        </h3>
        <div class="flex gap-2 items-center">
          <input
            type="text"
            class="bg-transparent border-b border-outline-variant text-on-surface
                   font-technical-data text-technical-data py-1 px-2 focus:outline-none
                   focus:border-primary placeholder-on-surface-variant"
            placeholder="Filter…"
            [(ngModel)]="filter"
          />
          <span
            class="font-technical-data text-technical-data text-on-surface-variant
                   bg-surface px-2 py-1 border border-outline-variant"
          >Total: {{ library.corpus().length }}</span>
        </div>
      </div>

      <div class="flex flex-col">
        <div
          class="grid grid-cols-12 gap-4 p-panel-padding border-b border-outline-variant
                 bg-surface-dim font-label-caps text-label-caps text-on-surface-variant
                 sticky top-0 z-10 uppercase"
        >
          <div class="col-span-6">Document Title</div>
          <div class="col-span-3 text-right">Ingested</div>
          <div class="col-span-2 text-right">Chunks</div>
          <div class="col-span-1 text-center">Status</div>
        </div>

        @if (filtered().length === 0) {
          <div
            class="p-gutter font-technical-data text-technical-data text-on-surface-variant text-center"
          >
            No indexed documents yet. Upload PDFs above to ingest them into ChromaDB.
          </div>
        }

        @for (doc of filtered(); track doc.id) {
          <div
            class="grid grid-cols-12 gap-4 p-panel-padding border-b border-outline-variant
                   bg-surface hover:bg-surface-variant transition-colors group items-center"
            [class.opacity-60]="doc.status === 'error'"
          >
            <div class="col-span-6 flex items-center gap-3 overflow-hidden">
              <span
                class="material-symbols-outlined text-sm"
                [class.text-error]="doc.status === 'error'"
                [class.text-on-surface-variant]="doc.status !== 'error'"
              >{{ docIcon(doc.type) }}</span>
              <span
                class="font-technical-data text-technical-data text-on-surface truncate
                       group-hover:text-primary transition-colors"
                [class.line-through]="doc.status === 'error'"
              >{{ doc.title }}</span>
            </div>
            <div class="col-span-3 text-right font-technical-data text-technical-data text-on-surface-variant">
              {{ doc.ingestedAt }}
            </div>
            <div class="col-span-2 text-right font-technical-data text-technical-data text-on-surface-variant">
              @if (doc.status === 'error') { -- } @else { {{ doc.chunks }} }
            </div>
            <div class="col-span-1 flex justify-center">
              <span
                class="w-2 h-2 rounded-full"
                [class.bg-tertiary-container]="doc.status === 'ready'"
                [class.bg-tertiary-fixed-dim]="doc.status === 'processing'"
                [class.bg-error]="doc.status === 'error'"
                [title]="doc.status"
              ></span>
            </div>
          </div>
        }
      </div>
    </section>
  `,
})
export class CorpusTableComponent {
  protected readonly library = inject(LibraryStore);
  protected readonly filter = signal('');

  protected readonly filtered = computed(() => {
    const q = this.filter().toLowerCase().trim();
    const list = this.library.corpus();
    return q ? list.filter((d) => d.title.toLowerCase().includes(q)) : list;
  });

  protected docIcon(type: string): string {
    switch (type) {
      case 'pdf': return 'picture_as_pdf';
      case 'md': return 'article';
      case 'txt': return 'description';
      default: return 'description';
    }
  }
}
