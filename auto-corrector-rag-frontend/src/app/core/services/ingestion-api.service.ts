import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../../environments/environment';
import {
  IngestDirectoryRequest,
  IngestResponse,
} from '../models/ingestion.model';

@Injectable({ providedIn: 'root' })
export class IngestionApiService {
  private readonly http = inject(HttpClient);
  private readonly base = `${environment.apiBaseUrl}/api/ingest`;

  ingestDirectory(body: IngestDirectoryRequest): Observable<IngestResponse> {
    return this.http.post<IngestResponse>(`${this.base}/pdfs`, body);
  }

  uploadFiles(files: File[]): Observable<IngestResponse> {
    const form = new FormData();
    files.forEach((f) => form.append('files', f, f.name));
    return this.http.post<IngestResponse>(`${this.base}/upload`, form);
  }
}
