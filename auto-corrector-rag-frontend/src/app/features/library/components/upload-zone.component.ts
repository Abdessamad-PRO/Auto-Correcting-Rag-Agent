import {
  ChangeDetectionStrategy,
  Component,
  inject,
  signal,
} from '@angular/core';

import { LibraryStore } from '../../../core/state/library.store';

@Component({
  selector: 'app-upload-zone',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <section
      class="bg-surface p-stack-loose min-h-[240px] flex flex-col justify-center items-center
             border border-dashed transition-colors cursor-pointer group relative overflow-hidden"
      [class.border-outline-variant]="!dragging()"
      [class.border-primary]="dragging()"
      (click)="pickerEl.click()"
      (dragover)="onDragOver($event)"
      (dragleave)="onDragLeave($event)"
      (drop)="onDrop($event)"
    >
      <div
        class="absolute inset-0 bg-primary/5 pointer-events-none transition-opacity"
        [class.opacity-100]="dragging()"
        [class.opacity-0]="!dragging()"
      ></div>

      <span
        class="material-symbols-outlined text-5xl mb-4 transition-colors"
        [class.text-on-surface-variant]="!dragging()"
        [class.text-primary]="dragging()"
      >cloud_upload</span>
      <h3 class="font-headline-sm text-headline-sm text-on-surface mb-2">
        Ingest New Documents
      </h3>
      <p class="font-technical-data text-technical-data text-on-surface-variant text-center max-w-md">
        Drag and drop PDF files here to process through the ingestion pipeline.
        Files are chunked, embedded, and added to ChromaDB.
      </p>

      <div class="mt-stack-loose">
        <span
          class="py-2 px-6 border border-outline text-on-surface group-hover:border-primary
                 group-hover:text-primary transition-colors font-label-caps text-label-caps uppercase"
        >Select Files</span>
      </div>

      <input
        #pickerEl
        type="file"
        accept=".pdf,application/pdf"
        multiple
        class="hidden"
        (change)="onPicked($event)"
        (click)="$event.stopPropagation()"
      />
    </section>
  `,
})
export class UploadZoneComponent {
  protected readonly library = inject(LibraryStore);
  protected readonly dragging = signal(false);

  protected onDragOver(ev: DragEvent): void {
    ev.preventDefault();
    this.dragging.set(true);
  }

  protected onDragLeave(ev: DragEvent): void {
    ev.preventDefault();
    this.dragging.set(false);
  }

  protected onDrop(ev: DragEvent): void {
    ev.preventDefault();
    this.dragging.set(false);
    const files = Array.from(ev.dataTransfer?.files ?? []).filter((f) =>
      f.name.toLowerCase().endsWith('.pdf'),
    );
    if (files.length) this.library.upload(files);
  }

  protected onPicked(ev: Event): void {
    const input = ev.target as HTMLInputElement;
    const files = Array.from(input.files ?? []);
    if (files.length) this.library.upload(files);
    input.value = '';
  }
}
