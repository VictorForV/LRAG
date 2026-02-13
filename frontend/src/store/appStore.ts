/**
 * Zustand store for global application state
 */

import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { User } from '../types';

interface AppState {
  // User authentication
  currentUser: User | null;
  isAuthenticated: boolean;
  setUser: (user: User | null) => void;
  login: (username: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  checkAuth: () => Promise<void>;

  // Theme
  theme: 'light' | 'dark';
  setTheme: (theme: 'light' | 'dark') => void;
  toggleTheme: () => void;

  // Current project
  currentProject: { id: string; name: string } | null;
  setCurrentProject: (project: { id: string; name: string } | null) => void;

  // Current session
  currentSession: { id: string; title: string } | null;
  setCurrentSession: (session: { id: string; title: string } | null) => void;

  // UI state
  sidebarOpen: boolean;
  setSidebarOpen: (open: boolean) => void;

  // Settings
  settingsDialogOpen: boolean;
  setSettingsDialogOpen: (open: boolean) => void;
}

export const useAppStore = create<AppState>()(
  persist(
    (set, _get) => ({
      // User authentication
      currentUser: null,
      isAuthenticated: false,

      setUser: (user) => set({ currentUser: user, isAuthenticated: user !== null }),

      login: async (username: string, password: string) => {
        const { authApi } = await import('../api/auth');
        const response = await authApi.login(username, password);
        set({
          currentUser: response,
          isAuthenticated: true,
        });
      },

      logout: async () => {
        try {
          const { authApi } = await import('../api/auth');
          await authApi.logout();
        } finally {
          set({
            currentUser: null,
            isAuthenticated: false,
            currentProject: null,
            currentSession: null,
          });
        }
      },

      checkAuth: async () => {
        try {
          const { authApi } = await import('../api/auth');
          const response = await authApi.verify();
          if (response.valid && response.user) {
            set({
              currentUser: response.user,
              isAuthenticated: true,
            });
          } else {
            set({
              currentUser: null,
              isAuthenticated: false,
            });
          }
        } catch {
          set({
            currentUser: null,
            isAuthenticated: false,
          });
        }
      },

      // Theme
      theme: 'light',
      setTheme: (theme) => {
        set({ theme });
        if (theme === 'dark') {
          document.documentElement.classList.add('dark');
        } else {
          document.documentElement.classList.remove('dark');
        }
      },
      toggleTheme: () => {
        set((state) => {
          const newTheme = state.theme === 'light' ? 'dark' : 'light';
          if (newTheme === 'dark') {
            document.documentElement.classList.add('dark');
          } else {
            document.documentElement.classList.remove('dark');
          }
          return { theme: newTheme };
        });
      },

      // Current project
      currentProject: null,
      setCurrentProject: (project) => set({ currentProject: project }),

      // Current session
      currentSession: null,
      setCurrentSession: (session) => set({ currentSession: session }),

      // UI state
      sidebarOpen: true,
      setSidebarOpen: (open) => set({ sidebarOpen: open }),

      // Settings
      settingsDialogOpen: false,
      setSettingsDialogOpen: (open) => set({ settingsDialogOpen: open }),
    }),
    {
      name: 'rag-app-store',
      partialize: (state) => ({
        theme: state.theme,
        currentProject: state.currentProject,
        currentSession: state.currentSession,
        currentUser: state.currentUser,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
);

export const initializeTheme = () => {
  const theme = useAppStore.getState().theme;
  if (theme === 'dark') {
    document.documentElement.classList.add('dark');
  } else {
    document.documentElement.classList.remove('dark');
  }
};
