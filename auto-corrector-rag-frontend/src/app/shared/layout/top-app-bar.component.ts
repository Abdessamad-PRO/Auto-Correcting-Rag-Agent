import {
  ChangeDetectionStrategy,
  Component,
  inject,
  input,
  output,
} from '@angular/core';

import { SystemStatusStore } from '../../core/state/system-status.store';

@Component({
  selector: 'app-top-app-bar',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <header
      class="bg-surface text-primary h-16 border-b border-outline-variant
             flex justify-between items-center px-margin-edge w-full shrink-0 z-20"
    >
      <div class="flex items-center gap-gutter min-w-0">
        <button
          type="button"
          class="md:hidden p-1 -ml-1 text-on-surface-variant hover:text-primary
                 transition-colors flex items-center justify-center"
          aria-label="Toggle menu"
          (click)="menuToggled.emit()"
        >
          <span class="material-symbols-outlined">menu</span>
        </button>

        <span class="font-headline-sm text-headline-sm font-bold text-primary tracking-tighter">
          RAG OS
        </span>
        <div class="h-6 w-px bg-outline-variant mx-1 hidden sm:block"></div>
        <h1 class="font-headline-sm text-headline-sm font-bold text-primary truncate hidden sm:block">
          {{ title() }}
        </h1>
      </div>

      <div class="flex items-center gap-3 sm:gap-gutter">
        <div class="relative hidden lg:block">
          <input
            type="text"
            placeholder="Search knowledge base..."
            class="w-56 xl:w-64 bg-transparent border-b border-outline-variant
                   focus:border-primary text-on-surface font-technical-data
                   text-technical-data py-1 px-0 focus:outline-none focus:ring-0
                   placeholder-on-surface-variant transition-colors"
          />
          <span
            class="material-symbols-outlined absolute right-0 top-1/2
                   -translate-y-1/2 text-on-surface-variant text-sm"
          >search</span>
        </div>

        <button
          type="button"
          class="p-2 text-on-surface-variant hover:text-primary transition-all
                 hover:scale-95 hidden sm:flex items-center justify-center"
          aria-label="Notifications"
        >
          <span class="material-symbols-outlined">notifications</span>
        </button>
        <button
          type="button"
          class="p-2 text-on-surface-variant hover:text-primary transition-all
                 hover:scale-95 hidden sm:flex items-center justify-center"
          aria-label="Terminal"
        >
          <span class="material-symbols-outlined">terminal</span>
        </button>

        <button
          type="button"
          class="hidden md:block px-3 lg:px-4 py-2 border border-tertiary-fixed-dim
                 text-tertiary-fixed-dim hover:bg-tertiary-fixed-dim hover:text-surface
                 transition-colors duration-150 font-label-caps text-label-caps uppercase"
        >
          Deploy
        </button>

        <div class="hidden md:flex flex-col text-right ml-1">
          <span class="font-label-caps text-label-caps text-on-surface-variant uppercase">
            Provider
          </span>
          <span class="font-technical-data text-technical-data text-tertiary-fixed-dim">
            {{ status.health()?.provider ?? '—' }}
          </span>
        </div>

        <div
          class="w-8 h-8 rounded-full bg-surface-variant border border-outline-variant
                 overflow-hidden flex-shrink-0 flex items-center justify-center
                 text-primary font-label-caps"
        >
          R
        </div>
      </div>
    </header>
  `,
})
export class TopAppBarComponent {
  readonly title = input<string>('Research Workspace');
  readonly menuToggled = output<void>();
  protected readonly status = inject(SystemStatusStore);
}
