/**
 * API functions for the RAG Agent backend
 */

import apiClient, { API_BASE_URL } from './client';
import type {
  Project,
  ProjectCreate,
  ProjectUpdate,
  Session,
  SessionCreate,
  SessionUpdate,
  Message,
  Document,
  UploadResult,
  Settings,
  SettingsUpdate,
  ChatRequest,
  ChatChunkEvent,
  HealthResponse,
} from '../types';

// ============================================================================
// PROJECTS API
// ============================================================================

export const projectsApi = {
  list: async (search?: string, limit = 100): Promise<Project[]> => {
    const params = search ? { search, limit } : { limit };
    const response = await apiClient.get<Project[]>('/api/projects', { params });
    return response.data;
  },

  get: async (projectId: string): Promise<Project> => {
    const response = await apiClient.get<Project>(`/api/projects/${projectId}`);
    return response.data;
  },

  create: async (data: ProjectCreate): Promise<Project> => {
    const response = await apiClient.post<Project>('/api/projects', data);
    return response.data;
  },

  update: async (projectId: string, data: ProjectUpdate): Promise<Project> => {
    const response = await apiClient.put<Project>(`/api/projects/${projectId}`, data);
    return response.data;
  },

  delete: async (projectId: string): Promise<void> => {
    await apiClient.delete(`/api/projects/${projectId}`);
  },
};

// ============================================================================
// SESSIONS API
// ============================================================================

export const sessionsApi = {
  list: async (projectId: string, limit = 50): Promise<Session[]> => {
    const response = await apiClient.get<Session[]>(`/api/projects/${projectId}/sessions`, {
      params: { limit },
    });
    return response.data;
  },

  get: async (sessionId: string): Promise<Session> => {
    const response = await apiClient.get<Session>(`/api/sessions/${sessionId}`);
    return response.data;
  },

  create: async (projectId: string, data: SessionCreate = {}): Promise<Session> => {
    const response = await apiClient.post<Session>(`/api/projects/${projectId}/sessions`, {
      title: data.title || 'New Chat',
    });
    return response.data;
  },

  update: async (sessionId: string, data: SessionUpdate): Promise<Session> => {
    const response = await apiClient.put<Session>(`/api/sessions/${sessionId}`, data);
    return response.data;
  },

  delete: async (sessionId: string): Promise<void> => {
    await apiClient.delete(`/api/sessions/${sessionId}`);
  },
};

// ============================================================================
// MESSAGES API
// ============================================================================

export const messagesApi = {
  list: async (sessionId: string, limit = 100): Promise<Message[]> => {
    const response = await apiClient.get<Message[]>(`/api/sessions/${sessionId}/messages`, {
      params: { limit },
    });
    return response.data;
  },

  create: async (sessionId: string, role: 'user' | 'assistant', content: string): Promise<Message> => {
    const response = await apiClient.post<Message>(`/api/sessions/${sessionId}/messages`, {
      role,
      content,
      metadata: {},
    });
    return response.data;
  },

  clear: async (sessionId: string): Promise<void> => {
    await apiClient.delete(`/api/sessions/${sessionId}/messages`);
  },
};

// ============================================================================
// DOCUMENTS API
// ============================================================================

export const documentsApi = {
  list: async (projectId: string, limit = 100): Promise<Document[]> => {
    const response = await apiClient.get<Document[]>(`/api/projects/${projectId}/documents`, {
      params: { limit },
    });
    return response.data;
  },

  get: async (documentId: string): Promise<Document> => {
    const response = await apiClient.get<Document>(`/api/documents/${documentId}`);
    return response.data;
  },

  delete: async (documentId: string): Promise<void> => {
    await apiClient.delete(`/api/documents/${documentId}`);
  },

  upload: async (projectId: string, files: File[]): Promise<UploadResult[]> => {
    const formData = new FormData();
    files.forEach((file) => {
      formData.append('files', file);
    });

    const response = await apiClient.post<UploadResult[]>(
      `/api/projects/${projectId}/upload`,
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      }
    );
    return response.data;
  },
};

// ============================================================================
// CHAT API (SSE STREAMING)
// ============================================================================

export interface ChatStreamCallbacks {
  onStart?: (data: ChatChunkEvent) => void;
  onChunk?: (data: ChatChunkEvent) => void;
  onDone?: (data: ChatChunkEvent) => void;
  onError?: (data: ChatChunkEvent) => void;
}

export const chatApi = {
  stream: async (request: ChatRequest, callbacks: ChatStreamCallbacks): Promise<void> => {
    const response = await fetch(`${API_BASE_URL}/api/chat/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      throw new Error(`Chat streaming failed: ${response.statusText}`);
    }

    const reader = response.body?.getReader();
    if (!reader) {
      throw new Error('No response body reader');
    }

    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });

      // Process SSE events
      const lines = buffer.split('\n');
      buffer = lines.pop() || ''; // Keep incomplete line in buffer

      for (let i = 0; i < lines.length; i++) {
        const line = lines[i].trim();
        if (!line) continue;

        if (line.startsWith('event:')) {
          const dataLine = lines[i + 1];
          if (dataLine && dataLine.startsWith('data:')) {
            try {
              const data: ChatChunkEvent = JSON.parse(dataLine.substring(5).trim());

              switch (data.event) {
                case 'start':
                  callbacks.onStart?.(data);
                  break;
                case 'chunk':
                  callbacks.onChunk?.(data);
                  break;
                case 'done':
                  callbacks.onDone?.(data);
                  break;
                case 'error':
                  callbacks.onError?.(data);
                  break;
              }
            } catch (e) {
              console.error('Failed to parse SSE data:', e);
            }
            i++; // Skip the data line we just processed
          }
        }
      }
    }
  },

  // Non-streaming fallback
  send: async (request: ChatRequest): Promise<{ content: string; session_id: string }> => {
    const response = await apiClient.post('/api/chat', request);
    return response.data;
  },
};

// ============================================================================
// SETTINGS API
// ============================================================================

export const settingsApi = {
  get: async (): Promise<Settings> => {
    const response = await apiClient.get<Settings>('/api/settings');
    return response.data;
  },

  update: async (data: SettingsUpdate): Promise<Settings> => {
    const response = await apiClient.put<Settings>('/api/settings', data);
    return response.data;
  },
};

// ============================================================================
// HEALTH API
// ============================================================================

export const healthApi = {
  check: async (): Promise<HealthResponse> => {
    const response = await apiClient.get<HealthResponse>('/health');
    return response.data;
  },
};
