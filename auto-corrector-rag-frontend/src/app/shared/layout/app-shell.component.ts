import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { NavigationEnd, Router, RouterOutlet } from '@angular/router';
import { toSignal } from '@angular/core/rxjs-interop';
import { filter, map, startWith } from 'rxjs';

import { SideNavComponent } from './side-nav.component';
import { StatusFooterComponent } from './status-footer.component';
import { TopAppBarComponent } from './top-app-bar.component';

const TITLES: Record<string, string> = {
  workspace: 'Research Workspace',
  library: 'Document Library',
  system: 'System Health',
};

@Component({
  selector: 'app-app-shell',
  standalone: true,
  imports: [RouterOutlet, SideNavComponent, TopAppBarComponent, StatusFooterComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="h-screen flex flex-col overflow-hidden">
      <app-top-app-bar [title]="pageTitle()" />

      <main class="flex-1 flex overflow-hidden">
        <app-side-nav />
        <section class="flex-1 flex flex-col bg-surface-container-lowest overflow-hidden relative">
          <router-outlet />
        </section>
      </main>

      <app-status-footer />
      <!-- Spacer for the fixed footer so content never sits beneath it -->
      <div class="h-8 shrink-0"></div>
    </div>
  `,
})
export class AppShellComponent {
  private readonly router = inject(Router);
  protected readonly pageTitle = toSignal(
    this.router.events.pipe(
      filter((e): e is NavigationEnd => e instanceof NavigationEnd),
      map((e) => TITLES[e.urlAfterRedirects.split('/')[1] ?? ''] ?? 'Research Workspace'),
      startWith(TITLES[this.router.url.split('/')[1] ?? ''] ?? 'Research Workspace'),
    ),
    { initialValue: 'Research Workspace' },
  );
}
