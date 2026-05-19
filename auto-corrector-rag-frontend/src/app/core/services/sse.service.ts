import { isPlatformBrowser } from '@angular/common';
import { Injectable, NgZone, PLATFORM_ID, inject } from '@angular/core';
import { Observable } from 'rxjs';

import {
  FinalEvent,
  InterruptEvent,
  SseEventName,
  SseMessage,
  TraceUpdate,
} from '../models/agent.model';

/**
 * Wraps the browser `EventSource` API into an Observable that emits typed
 * messages, runs callbacks inside the Angular zone, and closes the
 * connection on unsubscribe. Safe to call during SSR (returns an inert
 * Observable when not in the browser).
 */
@Injectable({ providedIn: 'root' })
export class SseService {
  private readonly zone = inject(NgZone);
  private readonly platformId = inject(PLATFORM_ID);

  connect(url: string): Observable<SseMessage<TraceUpdate | InterruptEvent | FinalEvent | unknown>> {
    if (!isPlatformBrowser(this.platformId)) {
      return new Observable((sub) => sub.complete());
    }

    return new Observable((subscriber) => {
      const es = new EventSource(url);

      const fwd = (event: SseEventName) => (ev: MessageEvent) => {
        let data: unknown = ev.data;
        try { data = JSON.parse(ev.data); } catch { /* ignore */ }
        this.zone.run(() => subscriber.next({ event, data }));
      };

      es.addEventListener('meta', fwd('meta'));
      es.addEventListener('update', fwd('update'));
      es.addEventListener('interrupt', fwd('interrupt'));
      es.addEventListener('final', (ev) => {
        fwd('final')(ev);
        this.zone.run(() => subscriber.complete());
        es.close();
      });
      es.onerror = (err) => {
        // Browser auto-reconnects; we surface the error to the caller and let
        // them decide whether to bail out.
        this.zone.run(() => subscriber.next({ event: 'error', data: err }));
      };

      return () => es.close();
    });
  }
}
