import {
  ChangeDetectionStrategy,
  Component,
  effect,
  inject,
  signal,
  PLATFORM_ID,
} from '@angular/core';
import { isPlatformBrowser } from '@angular/common';
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
      <app-top-app-bar
        [title]="pageTitle()"
        (menuToggled)="toggleNav()"
      />

      <main class="flex-1 flex overflow-hidden min-h-0 relative">
        <!-- Side nav: persistent on md+, drawer on mobile -->
        <app-side-nav
          [class.mobile-open]="navOpen()"
          (linkClicked)="closeNav()"
        />

        <!-- Backdrop appears on mobile when drawer is open -->
        @if (navOpen()) {
          <button
            type="button"
            class="mobile-backdrop md:hidden"
            aria-label="Close menu"
            (click)="closeNav()"
          ></button>
        }

        <section
          class="flex-1 flex flex-col bg-surface-container-lowest overflow-hidden relative min-w-0 min-h-0"
        >
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
  private readonly platformId = inject(PLATFORM_ID);

  protected readonly pageTitle = toSignal(
    this.router.events.pipe(
      filter((e): e is NavigationEnd => e instanceof NavigationEnd),
      map((e) => TITLES[e.urlAfterRedirects.split('/')[1] ?? ''] ?? 'Research Workspace'),
      startWith(TITLES[this.router.url.split('/')[1] ?? ''] ?? 'Research Workspace'),
    ),
    { initialValue: 'Research Workspace' },
  );

  protected readonly navOpen = signal<boolean>(false);

  constructor() {
    // Auto-close the drawer when the route changes (mobile UX).
    this.router.events
      .pipe(filter((e) => e instanceof NavigationEnd))
      .subscribe(() => this.closeNav());

    // Sync the .nav-open class onto <body> for backdrop visibility.
    effect(() => {
      if (!isPlatformBrowser(this.platformId)) return;
      document.body.classList.toggle('nav-open', this.navOpen());
    });
  }

  protected toggleNav(): void { this.navOpen.update((v) => !v); }
  protected closeNav(): void { this.navOpen.set(false); }
}
