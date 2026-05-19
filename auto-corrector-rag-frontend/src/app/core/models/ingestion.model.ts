export interface IngestDirectoryRequest {
  pdf_dir: string;
}

export interface IngestResponse {
  files_ingested: number;
  chunks_added: number;
  collection: string;
  persist_dir: string;
}

/** Local-only model used by the upload pipeline UI (not part of the backend API). */
export interface UploadTask {
  id: string;
  file: File;
  stage: 'queued' | 'uploading' | 'chunking' | 'embedding' | 'done' | 'error';
  progress: number;
  error?: string;
}

/** Local-only model used by the corpus table. */
export interface CorpusDocument {
  id: string;
  title: string;
  ingestedAt: string;
  chunks: number;
  status: 'ready' | 'processing' | 'error';
  type: 'pdf' | 'md' | 'txt' | 'other';
}
