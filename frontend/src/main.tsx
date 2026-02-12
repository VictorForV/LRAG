import { StrictMode, useEffect } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import './index.css'
import App from './App.tsx'
import AuthGuard from './components/AuthGuard'
import LoginPage from './pages/LoginPage'
import { initializeTheme } from './store/appStore'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

// Create React Query client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

function Root() {
  // Initialize theme on mount
  useEffect(() => {
    initializeTheme();
  }, []);

  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          {/* Public route - Login */}
          <Route path="/login" element={<LoginPage />} />

          {/* Protected routes - wrapped with AuthGuard */}
          <Route
            path="/*"
            element={
              <AuthGuard>
                <App />
              </AuthGuard>
            }
          />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <Root />
  </StrictMode>,
)
