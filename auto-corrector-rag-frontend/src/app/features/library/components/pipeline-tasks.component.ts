import { ChangeDetectionStrategy, Component, inject } from '@angular/core';

import { LibraryStore } from '../../../core/state/library.store';

@Component({
  selector: 'app-pipeline-tasks',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <section class="bg-surface p-gutter">
      <h3
        class="font-label-caps text-label-caps text-on-surface-variant uppercase tracking-widest
               mb-stack-compact flex items-center gap-2"
      >
        @if (library.activeTasks().length > 0) {
          <span class="w-2 h-2 rounded-full bg-tertiary-fixed-dim animate-pulse"></span>
        } @else {
          <span class="w-2 h-2 rounded-full bg-outline"></span>
        }
        Active Pipeline
        @if (library.tasks().length > 0) {
          <button
            type="button"
            class="ml-auto font-technical-data text-technical-data text-on-surface-variant
                   hover:text-primary"
            (click)="library.clearFinished()"
          >Clear finished</button>
        }
      </h3>

      @if (library.tasks().length === 0) {
        <p class="font-technical-data text-technical-data text-on-surface-variant py-3">
          No ingestion tasks running.
        </p>
      }

      <div class="flex flex-col gap-unit">
        @for (task of library.tasks(); track task.id) {
          <div
            class="border border-outline-variant p-panel-padding bg-surface-container-low
                   flex items-center gap-4"
          >
            <span
              class="material-symbols-outlined"
              [class.text-on-surface-variant]="task.stage !== 'error'"
              [class.text-error]="task.stage === 'error'"
            >{{ icon(task.stage) }}</span>

            <div class="flex-1 min-w-0">
              <div class="flex justify-between items-end mb-1 gap-2">
                <span class="font-technical-data text-technical-data text-on-surface truncate">
                  {{ task.file.name }}
                </span>
                <span
                  class="font-technical-data text-[10px] uppercase whitespace-nowrap"
                  [class.text-tertiary-fixed-dim]="task.stage !== 'error' && task.stage !== 'done'"
                  [class.text-on-surface-variant]="task.stage === 'done'"
                  [class.text-error]="task.stage === 'error'"
                >
                  {{ label(task.stage) }} · {{ task.progress }}%
                </span>
              </div>
              <div class="w-full h-1 bg-surface-container-highest overflow-hidden">
                <div
                  class="h-full transition-all duration-300"
                  [style.width.%]="task.progress"
                  [class.bg-tertiary-fixed-dim]="task.stage !== 'error' && task.stage !== 'done'"
                  [class.bg-primary]="task.stage === 'done'"
                  [class.bg-error]="task.stage === 'error'"
                ></div>
              </div>
              @if (task.error) {
                <p class="font-technical-data text-technical-data text-error mt-1">
                  {{ task.error }}
                </p>
              }
            </div>

            <button
              type="button"
              class="text-on-surface-variant hover:text-primary"
              (click)="library.removeTask(task.id)"
              aria-label="Remove task"
            >
              <span class="material-symbols-outlined text-sm">close</span>
            </button>
          </div>
        }
      </div>
    </section>
  `,
})
export class PipelineTasksComponent {
  protected readonly library = inject(LibraryStore);

  protected icon(stage: string): string {
    switch (stage) {
      case 'uploading': return 'upload';
      case 'chunking': return 'content_cut';
      case 'embedding': return 'memory';
      case 'done': return 'check_circle';
      case 'error': return 'error';
      default: return 'description';
    }
  }

  protected label(stage: string): string {
    switch (stage) {
      case 'uploading': return 'Uploading';
      case 'chunking': return 'Chunking';
      case 'embedding': return 'Embedding';
      case 'done': return 'Indexed';
      case 'error': return 'Failed';
      default: return 'Queued';
    }
  }
}
