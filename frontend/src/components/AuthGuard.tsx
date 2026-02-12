/**
 * AuthGuard - Protects routes and redirects to login if not authenticated
 */

import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAppStore } from '../store/appStore';

interface AuthGuardProps {
  children: React.ReactNode;
}

export default function AuthGuard({ children }: AuthGuardProps) {
  const navigate = useNavigate();
  const { isAuthenticated, checkAuth } = useAppStore();

  useEffect(() => {
    const checkAuthentication = async () => {
      // First, check auth status
      await checkAuth();

      // Then check if authenticated after the check completes
      const state = useAppStore.getState();
      if (!state.isAuthenticated) {
        navigate('/login', { replace: true });
      }
    };

    checkAuthentication();
  }, [checkAuth, navigate]);

  // Show nothing while checking or redirecting
  if (!isAuthenticated) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600 dark:border-indigo-400 mx-auto"></div>
          <p className="mt-4 text-gray-600 dark:text-gray-400">Loading...</p>
        </div>
      </div>
    );
  }

  return <>{children}</>;
}
