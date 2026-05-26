import { computed, inject, Injectable, signal } from '@angular/core';

import {
  CorpusDocument,
  CorpusEntry,
  UploadTask,
} from '../models/ingestion.model';
import { IngestionApiService } from '../services/ingestion-api.service';

let _uid = 0;
const nextId = () => `t_${Date.now()}_${++_uid}`;

const inferType = (name: string): CorpusDocument['type'] => {
  const n = name.toLowerCase();
  if (n.endsWith('.pdf')) return 'pdf';
  if (n.endsWith('.md')) return 'md';
  if (n.endsWith('.txt')) return 'txt';
  return 'other';
};

const basename = (path: string): string => {
  const parts = path.replace(/\\/g, '/').split('/');
  return parts[parts.length - 1] || path;
};

const corpusFromEntry = (e: CorpusEntry): CorpusDocument => ({
  id: e.id,
  title: e.title || basename(e.source),
  ingestedAt: '—',
  chunks: e.chunks,
  status: 'ready',
  type: inferType(e.title || e.source),
});

/** Library ViewModel — owns ingestion pipeline state and the corpus list. */
@Injectable({ providedIn: 'root' })
export class LibraryStore {
  private readonly api = inject(IngestionApiService);

  readonly tasks = signal<UploadTask[]>([]);
  readonly corpus = signal<CorpusDocument[]>([]);
  readonly busy = signal<boolean>(false);
  readonly loadingCorpus = signal<boolean>(false);
  readonly error = signal<string | null>(null);
  readonly collectionName = signal<string>('');

  readonly activeTasks = computed(() =>
    this.tasks().filter((t) => t.stage !== 'done' && t.stage !== 'error'),
  );
  readonly totalChunks = computed(() =>
    this.corpus().reduce((acc, d) => acc + d.chunks, 0),
  );

  /** Fetch the live corpus from ChromaDB. Called on every visit to /library. */
  loadCorpus(): void {
    this.loadingCorpus.set(true);
    this.api.listCorpus().subscribe({
      next: (resp) => {
        this.collectionName.set(resp.collection);
        this.corpus.set(resp.documents.map(corpusFromEntry));
        this.loadingCorpus.set(false);
      },
      error: (err) => {
        const detail =
          err?.error?.detail ?? err?.message ?? String(err);
        this.error.set(`Could not load corpus: ${detail}`);
        this.loadingCorpus.set(false);
      },
    });
  }

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
          if (curr.progress >= 45)
            return { ...curr, stage: 'chunking', progress: curr.progress + 5 };
          return { ...curr, progress: curr.progress + 6 };
        });
      }, 350),
    );

    this.api.uploadFiles(files).subscribe({
      next: () => {
        timers.forEach(clearInterval);
        fresh.forEach((t) =>
          this.updateTask(t.id, (c) => ({ ...c, stage: 'done', progress: 100 })),
        );
        // Replace synthetic numbers with the true post-ingest snapshot.
        this.loadCorpus();
        this.busy.set(false);
      },
      error: (err) => {
        timers.forEach(clearInterval);
        const detail =
          err?.error?.detail ??
          err?.error?.message ??
          err?.message ??
          String(err);
        fresh.forEach((t) =>
          this.updateTask(t.id, (c) => ({
            ...c,
            stage: 'error',
            error: String(detail),
          })),
        );
        this.error.set(String(detail));
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
