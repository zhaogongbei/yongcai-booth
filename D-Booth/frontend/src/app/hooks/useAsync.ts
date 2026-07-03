import { useState, useEffect, useCallback, useRef } from 'react';

/**
 * Async operation state
 */
export interface AsyncState<T, E = Error> {
  /** Response data */
  data: T | null;
  /** Whether the operation is in progress */
  loading: boolean;
  /** Error object if operation failed */
  error: E | null;
  /** Operation status */
  status: 'idle' | 'pending' | 'success' | 'error';
}

/**
 * Async operation options
 */
export interface UseAsyncOptions<T, E = Error> {
  /** Whether to execute immediately on mount (default: false) */
  immediate?: boolean;
  /** Callback invoked on success */
  onSuccess?: (data: T) => void;
  /** Callback invoked on error */
  onError?: (error: E) => void;
  /** Callback invoked when operation completes (success or error) */
  onSettled?: (data: T | null, error: E | null) => void;
  /** Dependencies array - when changed, re-executes if immediate is true */
  deps?: React.DependencyList;
}

/**
 * Async operation management hook
 *
 * Provides state management for asynchronous operations with automatic
 * loading, error, and data state tracking. Handles component unmount cleanup.
 *
 * @param asyncFunction - Async function to execute
 * @param options - Configuration options
 * @returns Async state and execution methods
 *
 * @example
 * ```tsx
 * // Basic usage
 * async function fetchUser(id: string) {
 *   const response = await fetch(`/api/users/${id}`);
 *   return response.json();
 * }
 *
 * function UserProfile({ userId }: { userId: string }) {
 *   const { data, loading, error, execute } = useAsync(
 *     () => fetchUser(userId),
 *     { immediate: true, deps: [userId] }
 *   );
 *
 *   if (loading) return <Spinner />;
 *   if (error) return <ErrorMessage error={error} />;
 *   if (!data) return null;
 *
 *   return <div>{data.name}</div>;
 * }
 *
 * // Manual execution with parameters
 * function CreateUser() {
 *   const createUser = useAsync(
 *     async (name: string, email: string) => {
 *       const response = await fetch('/api/users', {
 *         method: 'POST',
 *         body: JSON.stringify({ name, email }),
 *       });
 *       return response.json();
 *     },
 *     {
 *       onSuccess: (user) => {
 *         console.log('Created user:', user);
 *       },
 *       onError: (error) => {
 *         console.error('Failed to create user:', error);
 *       },
 *     }
 *   );
 *
 *   const handleSubmit = async () => {
 *     await createUser.execute('John Doe', 'john@example.com');
 *   };
 *
 *   return (
 *     <button onClick={handleSubmit} disabled={createUser.loading}>
 *       Create User
 *     </button>
 *   );
 * }
 *
 * // With retry logic
 * function DataFetcher() {
 *   const { data, loading, error, execute, retry } = useAsync(fetchData);
 *
 *   if (error) {
 *     return (
 *       <div>
 *         <p>Error: {error.message}</p>
 *         <button onClick={retry}>Retry</button>
 *       </div>
 *     );
 *   }
 *
 *   return <div>{data}</div>;
 * }
 * ```
 */
export function useAsync<T, E = Error, Args extends unknown[] = []>(
  asyncFunction: (...args: Args) => Promise<T>,
  options: UseAsyncOptions<T, E> = {}
): AsyncState<T, E> & {
  execute: (...args: Args) => Promise<T | null>;
  reset: () => void;
  retry: () => Promise<T | null>;
} {
  const { immediate = false, onSuccess, onError, onSettled, deps = [] } = options;

  const [state, setState] = useState<AsyncState<T, E>>({
    data: null,
    loading: false,
    error: null,
    status: 'idle',
  });

  const mountedRef = useRef(true);
  const lastArgsRef = useRef<Args | null>(null);
  const asyncFunctionRef = useRef(asyncFunction);

  // Keep function ref up to date
  useEffect(() => {
    asyncFunctionRef.current = asyncFunction;
  }, [asyncFunction]);

  // Cleanup on unmount
  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
    };
  }, []);

  /**
   * Execute the async function
   *
   * @param args - Arguments to pass to the async function
   * @returns Promise resolving to the result or null on error
   */
  const execute = useCallback(
    async (...args: Args): Promise<T | null> => {
      lastArgsRef.current = args;

      if (mountedRef.current) {
        setState({
          data: null,
          loading: true,
          error: null,
          status: 'pending',
        });
      }

      try {
        const data = await asyncFunctionRef.current(...args);

        if (mountedRef.current) {
          setState({
            data,
            loading: false,
            error: null,
            status: 'success',
          });

          onSuccess?.(data);
          onSettled?.(data, null);
        }

        return data;
      } catch (err) {
        const error = err as E;

        if (mountedRef.current) {
          setState({
            data: null,
            loading: false,
            error,
            status: 'error',
          });

          onError?.(error);
          onSettled?.(null, error);
        }

        return null;
      }
    },
    [onSuccess, onError, onSettled]
  );

  /**
   * Retry the last execution with the same arguments
   */
  const retry = useCallback(async (): Promise<T | null> => {
    if (lastArgsRef.current) {
      return execute(...lastArgsRef.current);
    }
    return execute(...([] as unknown as Args));
  }, [execute]);

  /**
   * Reset state to initial values
   */
  const reset = useCallback(() => {
    lastArgsRef.current = null;
    setState({
      data: null,
      loading: false,
      error: null,
      status: 'idle',
    });
  }, []);

  // Auto-execute on mount or when deps change
  useEffect(() => {
    if (immediate) {
      void execute(...([] as unknown as Args));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [immediate, ...deps]);

  return {
    ...state,
    execute,
    reset,
    retry,
  };
}

/**
 * Simplified async hook for data fetching
 *
 * Automatically executes on mount and provides loading/error/data states.
 *
 * @param asyncFunction - Async function to execute
 * @param deps - Dependencies array
 * @returns Async state
 *
 * @example
 * ```tsx
 * function UserList() {
 *   const { data: users, loading, error } = useFetch(
 *     async () => {
 *       const response = await fetch('/api/users');
 *       return response.json();
 *     },
 *     []
 *   );
 *
 *   if (loading) return <Spinner />;
 *   if (error) return <ErrorMessage error={error} />;
 *
 *   return (
 *     <ul>
 *       {users?.map(user => <li key={user.id}>{user.name}</li>)}
 *     </ul>
 *   );
 * }
 * ```
 */
export function useFetch<T, E = Error>(
  asyncFunction: () => Promise<T>,
  deps: React.DependencyList = []
): AsyncState<T, E> & {
  refetch: () => Promise<T | null>;
} {
  const { execute, ...state } = useAsync<T, E, []>(asyncFunction, {
    immediate: true,
    deps,
  });

  return {
    ...state,
    refetch: execute,
  };
}
