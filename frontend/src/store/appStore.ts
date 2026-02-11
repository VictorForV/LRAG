/**
 * Zustand store for global application state
 */

import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface AppState {
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
    (set) => ({
      // Theme
      theme: 'light',
      setTheme: (theme) => {
        set({ theme });
        // Apply theme class to document
        if (theme === 'dark') {
          document.documentElement.classList.add('dark');
        } else {
          document.documentElement.classList.remove('dark');
        }
      },
      toggleTheme: () => {
        set((state) => {
          const newTheme = state.theme === 'light' ? 'dark' : 'light';
          // Apply theme class
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
      }),
    }
  )
);

// Initialize theme on load
export const initializeTheme = () => {
  const theme = useAppStore.getState().theme;
  if (theme === 'dark') {
    document.documentElement.classList.add('dark');
  } else {
    document.documentElement.classList.remove('dark');
  }
};
