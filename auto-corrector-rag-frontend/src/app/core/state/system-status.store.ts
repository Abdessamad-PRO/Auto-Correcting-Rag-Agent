import { effect, inject, Injectable, signal, PLATFORM_ID } from '@angular/core';
import { isPlatformBrowser } from '@angular/common';

import { HealthResponse } from '../models/health.model';
import { HealthApiService } from '../services/health-api.service';

/** Lightweight global status — used by the footer and the System Health page. */
@Injectable({ providedIn: 'root' })
export class SystemStatusStore {
  private readonly api = inject(HealthApiService);
  private readonly platformId = inject(PLATFORM_ID);

  readonly health = signal<HealthResponse | null>(null);
  readonly latencyMs = signal<number | null>(null);
  readonly online = signal<boolean>(false);
  readonly error = signal<string | null>(null);

  constructor() {
    // Auto-refresh in the browser only (SSE/HTTP requires browser runtime).
    if (isPlatformBrowser(this.platformId)) {
      this.refresh();
      setInterval(() => this.refresh(), 15_000);
    }
  }

  refresh(): void {
    const t0 = performance.now();
    this.api.health().subscribe({
      next: (h) => {
        this.health.set(h);
        this.latencyMs.set(Math.round(performance.now() - t0));
        this.online.set(true);
        this.error.set(null);
      },
      error: (err) => {
        this.online.set(false);
        this.error.set(String(err?.message ?? err));
      },
    });
  }
}
