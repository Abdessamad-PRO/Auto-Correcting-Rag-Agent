import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { RouterLink, RouterLinkActive } from '@angular/router';

import { AgentSessionStore } from '../../core/state/agent-session.store';

@Component({
  selector: 'app-side-nav',
  standalone: true,
  imports: [RouterLink, RouterLinkActive],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <nav
      class="hidden md:flex flex-col flex-shrink-0 h-full w-64 border-r
             border-outline-variant bg-surface py-panel-padding z-10"
    >
      <div class="px-gutter mb-stack-loose">
        <div class="flex items-center gap-2">
          <span class="material-symbols-outlined text-primary">grid_view</span>
          <h1 class="font-headline-sm text-headline-sm font-bold text-primary tracking-tighter">
            RAG OS
          </h1>
        </div>
        <p class="font-technical-data text-technical-data text-on-surface-variant mt-unit">
          v0.2.0 — research-agent
        </p>
      </div>

      <div class="px-gutter mb-stack-loose">
        <button
          type="button"
          (click)="newSession()"
          class="w-full py-2 px-4 border border-outline text-on-surface
                 hover:bg-primary hover:text-on-primary transition-colors duration-150
                 font-label-caps text-label-caps flex items-center justify-center gap-2"
        >
          <span class="material-symbols-outlined text-sm">add</span>
          New Session
        </button>
      </div>

      <div class="flex-1 overflow-y-auto cyber-scroll flex flex-col gap-1 px-2">
        <a
          routerLink="/workspace"
          routerLinkActive="active-link"
          class="nav-link"
        >
          <span class="material-symbols-outlined">history</span>
          <span class="font-label-caps text-label-caps">Research Sessions</span>
        </a>
        <a
          routerLink="/library"
          routerLinkActive="active-link"
          class="nav-link"
        >
          <span class="material-symbols-outlined">inventory_2</span>
          <span class="font-label-caps text-label-caps">Document Library</span>
        </a>
        <a
          routerLink="/system"
          routerLinkActive="active-link"
          class="nav-link"
        >
          <span class="material-symbols-outlined">analytics</span>
          <span class="font-label-caps text-label-caps">System Health</span>
        </a>
      </div>

      <div class="mt-auto flex flex-col gap-1 px-2 pt-4 border-t border-outline-variant">
        <a class="nav-link" href="#">
          <span class="material-symbols-outlined">settings</span>
          <span class="font-label-caps text-label-caps">Settings</span>
        </a>
        <a
          class="nav-link"
          href="http://localhost:8000/docs"
          target="_blank"
          rel="noopener"
        >
          <span class="material-symbols-outlined">menu_book</span>
          <span class="font-label-caps text-label-caps">API Docs</span>
        </a>
      </div>
    </nav>
  `,
  styles: [`
    .nav-link {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 8px 12px;
      color: var(--color-on-surface-variant);
      font-weight: 500;
      border-left: 2px solid transparent;
      transition: background-color 150ms;
    }
    .nav-link:hover {
      background-color: var(--color-surface-variant);
    }
    .nav-link.active-link {
      color: var(--color-primary);
      font-weight: 700;
      border-left-color: var(--color-primary);
      background-color: var(--color-surface-container-high);
      opacity: 0.9;
    }
  `],
})
export class SideNavComponent {
  private readonly session = inject(AgentSessionStore);

  newSession(): void {
    this.session.reset();
  }
}
