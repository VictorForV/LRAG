/**
 * TypeScript type definitions for the RAG Agent API
 */

// ============================================================================
// TYPES
// ============================================================================

export interface Project {
  id: string;
  name: string;
  description: string | null;
  created_at: string;
  updated_at: string;
  doc_count: number;
  session_count: number;
}

export interface Session {
  id: string;
  project_id: string;
  title: string;
  created_at: string;
  updated_at: string;
  message_count: number;
}

export interface Message {
  id: string;
  session_id: string;
  role: 'user' | 'assistant';
  content: string;
  metadata: Record<string, unknown>;
  created_at: string;
}

export interface Document {
  id: string;
  title: string;
  source: string;
  uri: string | null;
  metadata: Record<string, unknown>;
  project_id: string | null;
  first_ingested: string;
  last_ingested: string;
  ingestion_count: number;
  chunk_count: number | null;
}

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
}

export interface Settings {
  llm_model: string;
  embedding_model: string;
  audio_model: string;
  database_name: string;
  database_connected: boolean;
  llm_api_key_configured: boolean;
  embedding_api_key_configured: boolean;
  llm_provider: string;
  embedding_dimension: number;
}

export interface UploadResult {
  filename: string;
  success: boolean;
  chunks: number;
  status: string;
  error?: string;
}

// ============================================================================
// REQUEST TYPES
// ============================================================================

export interface ProjectCreate {
  name: string;
  description?: string;
}

export interface ProjectUpdate {
  name?: string;
  description?: string;
}

export interface SessionCreate {
  title?: string;
}

export interface SessionUpdate {
  title: string;
}

export interface ChatRequest {
  session_id: string;
  project_id: string;
  message: string;
  message_history: ChatMessage[];
}

export interface SettingsUpdate {
  llm_api_key?: string;
  llm_model?: string;
  embedding_api_key?: string;
  embedding_model?: string;
  audio_model?: string;
  database_url?: string;
}

// ============================================================================
// RESPONSE TYPES
// ============================================================================

export interface HealthResponse {
  status: string;
  database_connected: boolean;
  version: string;
}

export interface ChatChunkEvent {
  event: 'start' | 'chunk' | 'done' | 'error';
  content: string;
  session_id?: string;
  message_id?: string;
}
