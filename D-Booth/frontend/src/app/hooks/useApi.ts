import { useState, useEffect, useCallback, useRef } from 'react';
import { request, type RequestOptions, ApiError } from '../../lib/api';

/**
 * API request state
 */
export interface ApiState<T> {
  /** Response data */
  data: T | null;
  /** Whether the request is in progress */
  loading: boolean;
  /** Error object if request failed */
  error: Error | null;
  /** HTTP status code of the last response */
  status: number | null;
}

/**
 * API hook options
 */
export interface UseApiOptions<T> extends Omit<RequestOptions, 'method' | 'body'> {
  /** Whether to execute the request immediately on mount (default: true) */
  immediate?: boolean;
  /** Callback invoked on successful response */
  onSuccess?: (data: T) => void;
  /** Callback invoked on error */
  onError?: (error: Error) => void;
  /** Debounce delay in milliseconds (default: 0, no debounce) */
  debounce?: number;
  /** Dependencies array - when changed, re-executes the request if immediate is true */
  deps?: React.DependencyList;
}

/**
 * Generic API request hook with loading, error, and data state management
 *
 * Provides automatic state management for API requests including loading states,
 * error handling, and data caching. Supports manual and automatic execution,
 * debouncing, and request cancellation.
 *
 * @param path - API endpoint path
 * @param options - Request options
 * @returns API state and execution methods
 *
 * @example
 * ```tsx
 * // Automatic fetch on mount
 * function UserProfile({ userId }: { userId: string }) {
 *   const { data, loading, error } = useApi<User>(`/users/${userId}`);
 *
 *   if (loading) return <Spinner />;
 *   if (error) return <ErrorMessage error={error} />;
 *   if (!data) return null;
 *
 *   return <div>{data.name}</div>;
 * }
 *
 * // Manual execution
 * function CreateUserButton() {
 *   const { execute, loading } = useApi<User>('/users', {
 *     method: 'POST',
 *     immediate: false,
 *   });
 *
 *   const handleCreate = async () => {
 *     const user = await execute({ name: 'John' });
 *     console.log('Created:', user);
 *   };
 *
 *   return <button onClick={handleCreate} disabled={loading}>Create</button>;
 * }
 *
 * // With debouncing for search
 * function SearchBox() {
 *   const [query, setQuery] = useState('');
 *   const { data, loading } = useApi<SearchResults>('/search', {
 *     query: { q: query },
 *     debounce: 300,
 *     deps: [query],
 *   });
 *
 *   return (
 *     <>
 *       <input value={query} onChange={e => setQuery(e.target.value)} />
 *       {loading && <Spinner />}
 *       {data && <Results items={data.items} />}
 *     </>
 *   );
 * }
 * ```
 */
export function useApi<T = unknown>(
  path: string,
  options: UseApiOptions<T> = {}
): ApiState<T> & {
  execute: (body?: unknown) => Promise<T | null>;
  refresh: () => Promise<void>;
  reset: () => void;
} {
  const {
    immediate = true,
    onSuccess,
    onError,
    debounce = 0,
    deps = [],
    ...requestOptions
  } = options;

  const [state, setState] = useState<ApiState<T>>({
    data: null,
    loading: immediate,
    error: null,
    status: null,
  });

  const abortControllerRef = useRef<AbortController | null>(null);
  const debounceTimerRef = useRef<NodeJS.Timeout | null>(null);
  const mountedRef = useRef(true);

  // Cleanup on unmount
  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
      abortControllerRef.current?.abort();
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }
    };
  }, []);

  /**
   * Execute the API request
   *
   * @param body - Request body (for POST, PUT, PATCH)
   * @returns Promise resolving to response data or null on error
   */
  const execute = useCallback(
    async (body?: unknown): Promise<T | null> => {
      // Cancel previous request
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }

      // Clear previous debounce timer
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }

      // Debounced execution
      if (debounce > 0) {
        return new Promise((resolve) => {
          debounceTimerRef.current = setTimeout(async () => {
            const result = await execute(body);
            resolve(result);
          }, debounce);
        });
      }

      const controller = new AbortController();
      abortControllerRef.current = controller;

      if (mountedRef.current) {
        setState(prev => ({ ...prev, loading: true, error: null }));
      }

      try {
        const data = await request<T>(path, {
          ...requestOptions,
          body,
          signal: controller.signal,
        });

        if (mountedRef.current) {
          setState({
            data,
            loading: false,
            error: null,
            status: 200,
          });
          onSuccess?.(data);
        }

        return data;
      } catch (err) {
        if (mountedRef.current) {
          const error = err instanceof Error ? err : new Error('Unknown error');
          const status = err instanceof ApiError ? err.status : null;

          setState({
            data: null,
            loading: false,
            error,
            status,
          });

          onError?.(error);
        }

        return null;
      }
    },
    [path, debounce, onSuccess, onError, requestOptions]
  );

  /**
   * Refresh the request (re-execute with same parameters)
   */
  const refresh = useCallback(async () => {
    await execute();
  }, [execute]);

  /**
   * Reset state to initial values
   */
  const reset = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
    }
    setState({
      data: null,
      loading: false,
      error: null,
      status: null,
    });
  }, []);

  // Auto-execute on mount or when deps change
  useEffect(() => {
    if (immediate) {
      void execute();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [immediate, ...deps]);

  return {
    ...state,
    execute,
    refresh,
    reset,
  };
}

/**
 * Simplified hook for GET requests
 *
 * @param path - API endpoint path
 * @param options - Request options
 * @returns API state and methods
 *
 * @example
 * ```tsx
 * function EventList() {
 *   const { data: events, loading, error } = useGet<Event[]>('/events');
 *   // ...
 * }
 * ```
 */
export function useGet<T = unknown>(
  path: string,
  options: Omit<UseApiOptions<T>, 'method'> = {}
) {
  return useApi<T>(path, { ...options, method: 'GET' });
}

/**
 * Simplified hook for POST requests (not executed immediately)
 *
 * @param path - API endpoint path
 * @param options - Request options
 * @returns API state and methods
 *
 * @example
 * ```tsx
 * function CreateEventButton() {
 *   const { execute, loading } = usePost<Event>('/events');
 *
 *   const handleCreate = async () => {
 *     const event = await execute({ name: 'New Event' });
 *     // ...
 *   };
 *   // ...
 * }
 * ```
 */
export function usePost<T = unknown>(
  path: string,
  options: Omit<UseApiOptions<T>, 'method' | 'immediate'> = {}
) {
  return useApi<T>(path, { ...options, method: 'POST', immediate: false });
}

/**
 * Simplified hook for PUT requests (not executed immediately)
 *
 * @param path - API endpoint path
 * @param options - Request options
 * @returns API state and methods
 */
export function usePut<T = unknown>(
  path: string,
  options: Omit<UseApiOptions<T>, 'method' | 'immediate'> = {}
) {
  return useApi<T>(path, { ...options, method: 'PUT', immediate: false });
}

/**
 * Simplified hook for DELETE requests (not executed immediately)
 *
 * @param path - API endpoint path
 * @param options - Request options
 * @returns API state and methods
 */
export function useDelete<T = unknown>(
  path: string,
  options: Omit<UseApiOptions<T>, 'method' | 'immediate'> = {}
) {
  return useApi<T>(path, { ...options, method: 'DELETE', immediate: false });
}
