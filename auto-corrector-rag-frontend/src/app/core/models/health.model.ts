export interface HealthResponse {
  status: 'ok';
  provider: 'gemini' | 'openai' | 'grok' | string;
  model: string;
  chroma_collection: string;
  chroma_persist_dir: string;
  web_search_provider: 'duckduckgo' | 'tavily' | string;
}
