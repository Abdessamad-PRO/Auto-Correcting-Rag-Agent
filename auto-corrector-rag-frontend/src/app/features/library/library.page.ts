import { ChangeDetectionStrategy, Component } from '@angular/core';

import { CorpusTableComponent } from './components/corpus-table.component';
import { EvaluationConsoleComponent } from './components/evaluation-console.component';
import { PipelineTasksComponent } from './components/pipeline-tasks.component';
import { UploadZoneComponent } from './components/upload-zone.component';

@Component({
  selector: 'app-library-page',
  standalone: true,
  imports: [
    CorpusTableComponent,
    EvaluationConsoleComponent,
    PipelineTasksComponent,
    UploadZoneComponent,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <main class="flex-1 overflow-y-auto cyber-scroll p-gutter relative">
      <div class="max-w-[1600px] mx-auto grid grid-cols-1 lg:grid-cols-12 gap-px bg-outline-variant">
        <!-- Left: ingestion + corpus -->
        <div class="lg:col-span-8 flex flex-col gap-px">
          <app-upload-zone />
          <app-pipeline-tasks />
          <app-corpus-table />
        </div>

        <!-- Right: A/B evaluation -->
        <div class="lg:col-span-4">
          <app-evaluation-console />
        </div>
      </div>
    </main>
  `,
})
export class LibraryPage {}
