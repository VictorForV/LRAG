/**
 * Authentication API client
 */

import apiClient from './client';
import type { User, LoginResponse } from '../types';

// ============================================================================
// AUTH API
// ============================================================================

export interface UserLogin {
  username: string;
  password: string;
}

export interface LoginResponse extends User {
  access_token: string;
  token_type: string;
}

export interface TokenVerifyResponse {
  valid: boolean;
  user: User | null;
}

export interface UserSettings {
  id: string;
  user_id: string;
  llm_api_key: string | null;
  llm_model: string | null;
  llm_base_url: string | null;
  llm_provider: string | null;
  embedding_api_key: string | null;
  embedding_model: string | null;
  embedding_base_url: string | null;
  embedding_provider: string | null;
  embedding_dimension: number | null;
  audio_model: string | null;
  search_preferences: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface UserSettingsUpdate {
  llm_api_key?: string;
  llm_model?: string;
  llm_base_url?: string;
  llm_provider?: string;
  embedding_api_key?: string;
  embedding_model?: string;
  embedding_base_url?: string;
  embedding_provider?: string;
  embedding_dimension?: number;
  audio_model?: string;
  search_preferences?: Record<string, unknown>;
}

export const authApi = {
  /**
   * Login with username and password
   */
  login: async (username: string, password: string): Promise<LoginResponse> => {
    const response = await apiClient.post<LoginResponse>('/api/auth/login', {
      username,
      password,
    });
    return response.data;
  },

  /**
   * Logout current user
   */
  logout: async (): Promise<void> => {
    await apiClient.post('/api/auth/logout');
  },

  /**
   * Get current user info
   */
  me: async (): Promise<User> => {
    const response = await apiClient.get<User>('/api/auth/me');
    return response.data;
  },

  /**
   * Verify session token
   */
  verify: async (): Promise<TokenVerifyResponse> => {
    const response = await apiClient.get<TokenVerifyResponse>('/api/auth/verify');
    return response.data;
  },

  /**
   * Get user settings
   */
  getSettings: async (): Promise<UserSettings> => {
    const response = await apiClient.get<UserSettings>('/api/auth/settings');
    return response.data;
  },

  /**
   * Update user settings
   */
  updateSettings: async (data: UserSettingsUpdate): Promise<UserSettings> => {
    const response = await apiClient.put<UserSettings>('/api/auth/settings', data);
    return response.data;
  },
};
