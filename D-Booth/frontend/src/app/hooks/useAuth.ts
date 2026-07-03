import { useState, useEffect, useCallback } from 'react';
import { loginForm, tokenStorage, type LoginResponse } from '../../lib/api';

/**
 * Authentication state
 */
export interface AuthState {
  /** Whether the user is authenticated */
  isAuthenticated: boolean;
  /** Whether the auth state is being initialized */
  isLoading: boolean;
  /** Access token */
  token: string | null;
  /** Refresh token */
  refreshToken: string | null;
}

/**
 * Login parameters
 */
export interface LoginParams {
  username: string;
  password: string;
}

/**
 * Authentication hook
 *
 * Manages authentication state, login, logout, and automatic token refresh.
 * Listens to 'aibooth:unauthorized' events to clear auth state on token expiry.
 *
 * @returns Authentication state and methods
 *
 * @example
 * ```tsx
 * function LoginScreen() {
 *   const { isAuthenticated, login, logout, isLoading, error } = useAuth();
 *
 *   const handleLogin = async () => {
 *     const success = await login({ username: 'user', password: 'pass' });
 *     if (success) {
 *       navigate('/dashboard');
 *     }
 *   };
 *
 *   if (isAuthenticated) {
 *     return <button onClick={logout}>Logout</button>;
 *   }
 *
 *   return <button onClick={handleLogin}>Login</button>;
 * }
 * ```
 */
export function useAuth() {
  const [authState, setAuthState] = useState<AuthState>(() => {
    // Initialize from storage to avoid flash of unauthenticated state
    if (typeof window !== 'undefined') {
      const token = tokenStorage.access;
      const refreshToken = tokenStorage.refresh;
      return {
        isAuthenticated: !!token,
        isLoading: false,
        token,
        refreshToken,
      };
    }
    return {
      isAuthenticated: false,
      isLoading: true,
      token: null,
      refreshToken: null,
    };
  });
  const [error, setError] = useState<string | null>(null);

  // Listen for unauthorized events
  useEffect(() => {
    const handleUnauthorized = () => {
      tokenStorage.clear();
      setAuthState({
        isAuthenticated: false,
        isLoading: false,
        token: null,
        refreshToken: null,
      });
      setError('Session expired. Please login again.');
    };

    if (typeof window !== 'undefined') {
      window.addEventListener('aibooth:unauthorized', handleUnauthorized);
      return () => window.removeEventListener('aibooth:unauthorized', handleUnauthorized);
    }
  }, []);

  /**
   * Login with username and password
   *
   * @param params - Login credentials
   * @returns Promise resolving to true if login succeeded, false otherwise
   */
  const login = useCallback(async (params: LoginParams): Promise<boolean> => {
    setError(null);
    setAuthState(prev => ({ ...prev, isLoading: true }));

    try {
      const response: LoginResponse = await loginForm(params.username, params.password);

      tokenStorage.set(response.access_token, response.refresh_token);

      setAuthState({
        isAuthenticated: true,
        isLoading: false,
        token: response.access_token,
        refreshToken: response.refresh_token,
      });

      return true;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Login failed';
      setError(message);

      setAuthState({
        isAuthenticated: false,
        isLoading: false,
        token: null,
        refreshToken: null,
      });

      return false;
    }
  }, []);

  /**
   * Logout and clear authentication state
   */
  const logout = useCallback(() => {
    tokenStorage.clear();

    setAuthState({
      isAuthenticated: false,
      isLoading: false,
      token: null,
      refreshToken: null,
    });

    setError(null);
  }, []);

  /**
   * Clear error message
   */
  const clearError = useCallback(() => {
    setError(null);
  }, []);

  return {
    ...authState,
    login,
    logout,
    error,
    clearError,
  };
}
