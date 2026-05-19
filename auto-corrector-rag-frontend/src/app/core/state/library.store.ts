import { computed, inject, Injectable, signal } from '@angular/core';

import { CorpusDocument, UploadTask } from '../models/ingestion.model';
import { IngestionApiService } from '../services/ingestion-api.service';

let _uid = 0;
const nextId = () => `t_${Date.now()}_${++_uid}`;

/** Library ViewModel — owns ingestion pipeline state and the corpus list. */
@Injectable({ providedIn: 'root' })
export class LibraryStore {
  private readonly api = inject(IngestionApiService);

  readonly tasks = signal<UploadTask[]>([]);
  readonly corpus = signal<CorpusDocument[]>([]);
  readonly busy = signal<boolean>(false);
  readonly error = signal<string | null>(null);

  readonly activeTasks = computed(() =>
    this.tasks().filter((t) => t.stage !== 'done' && t.stage !== 'error'),
  );
  readonly totalChunks = computed(() =>
    this.corpus().reduce((acc, d) => acc + d.chunks, 0),
  );

  /** Push files into the pipeline and POST them to the backend. */
  upload(files: File[]): void {
    if (!files.length) return;
    this.error.set(null);

    const fresh: UploadTask[] = files.map((file) => ({
      id: nextId(),
      file,
      stage: 'uploading',
      progress: 5,
    }));
    this.tasks.update((prev) => [...fresh, ...prev]);
    this.busy.set(true);

    // Synthetic progress while the request is in flight — backend ingestion
    // is a single round-trip call without per-file events.
    const timers = fresh.map((t) =>
      setInterval(() => {
        this.updateTask(t.id, (curr) => {
          if (curr.progress >= 85) return { ...curr, stage: 'embedding' };
          if (curr.progress >= 45) return { ...curr, stage: 'chunking', progress: curr.progress + 5 };
          return { ...curr, progress: curr.progress + 6 };
        });
      }, 350),
    );

    this.api.uploadFiles(files).subscribe({
      next: (resp) => {
        timers.forEach(clearInterval);
        fresh.forEach((t) =>
          this.updateTask(t.id, (c) => ({ ...c, stage: 'done', progress: 100 })),
        );
        // Materialise the newly indexed files in the corpus list.
        const today = new Date().toISOString().slice(0, 10);
        const newDocs: CorpusDocument[] = files.map((f) => ({
          id: nextId(),
          title: f.name,
          ingestedAt: today,
          chunks: Math.max(1, Math.round(resp.chunks_added / files.length)),
          status: 'ready',
          type: f.name.toLowerCase().endsWith('.pdf')
            ? 'pdf'
            : f.name.toLowerCase().endsWith('.md')
              ? 'md'
              : f.name.toLowerCase().endsWith('.txt')
                ? 'txt'
                : 'other',
        }));
        this.corpus.update((prev) => [...newDocs, ...prev]);
        this.busy.set(false);
      },
      error: (err) => {
        timers.forEach(clearInterval);
        fresh.forEach((t) =>
          this.updateTask(t.id, (c) => ({ ...c, stage: 'error', error: String(err?.message ?? err) })),
        );
        this.error.set(String(err?.message ?? err));
        this.busy.set(false);
      },
    });
  }

  removeTask(id: string): void {
    this.tasks.update((prev) => prev.filter((t) => t.id !== id));
  }

  clearFinished(): void {
    this.tasks.update((prev) => prev.filter((t) => t.stage !== 'done'));
  }

  private updateTask(id: string, updater: (t: UploadTask) => UploadTask): void {
    this.tasks.update((prev) => prev.map((t) => (t.id === id ? updater(t) : t)));
  }
}
