import { useCallback, useEffect, useRef, useState } from 'react';
import type { DependencyList } from 'react';

export type HttpMethod = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';

export interface HttpFetchState<TData> {
  data: TData | null;
  loading: boolean;
  error: Error | null;
  status: number | null;
  statusText: string | null;
}

export interface UseHttpFetchOptions<TData, TBody = unknown> {
  method?: HttpMethod;
  headers?: HeadersInit;
  body?: TBody;
  query?: Record<string, string | number | boolean | null | undefined>;
  immediate?: boolean;
  deps?: DependencyList;
  timeoutMs?: number;
  retries?: number;
  retryDelayMs?: number;
  parseResponse?: (response: Response) => Promise<TData>;
  onSuccess?: (data: TData) => void;
  onError?: (error: Error) => void;
}

export class HttpFetchError extends Error {
  status: number;
  statusText: string;

  constructor(response: Response) {
    super(`HTTP ${response.status}: ${response.statusText}`);
    this.name = 'HttpFetchError';
    this.status = response.status;
    this.statusText = response.statusText;
  }
}

const DEFAULT_TIMEOUT_MS = 30000;
const DEFAULT_RETRY_DELAY_MS = 1000;

async function parseJsonResponse<TData>(response: Response): Promise<TData> {
  if (response.status === 204) {
    return null as TData;
  }

  const text = await response.text();
  if (!text) {
    return null as TData;
  }

  return JSON.parse(text) as TData;
}

function buildUrl(
  url: string,
  query?: Record<string, string | number | boolean | null | undefined>
): string {
  if (!query) {
    return url;
  }

  const params = new URLSearchParams();
  Object.entries(query).forEach(([key, value]) => {
    if (value !== null && value !== undefined) {
      params.append(key, String(value));
    }
  });

  const queryString = params.toString();
  if (!queryString) {
    return url;
  }

  return `${url}${url.includes('?') ? '&' : '?'}${queryString}`;
}

function applyRequestBody<TBody>(headers: Headers, body: TBody | undefined): BodyInit | undefined {
  if (body === undefined || body === null) {
    return undefined;
  }

  if (
    typeof body === 'string' ||
    body instanceof Blob ||
    body instanceof FormData ||
    body instanceof URLSearchParams ||
    body instanceof ArrayBuffer
  ) {
    return body;
  }

  if (!headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }

  return JSON.stringify(body);
}

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

export function useHttpFetch<TData = unknown, TBody = unknown>(
  url: string,
  options: UseHttpFetchOptions<TData, TBody> = {}
): HttpFetchState<TData> & {
  execute: (overrides?: Partial<UseHttpFetchOptions<TData, TBody>>) => Promise<TData | null>;
  refetch: () => Promise<TData | null>;
  cancel: () => void;
  reset: () => void;
} {
  const {
    method = 'GET',
    headers,
    body,
    query,
    immediate = true,
    deps = [],
    timeoutMs = DEFAULT_TIMEOUT_MS,
    retries = 0,
    retryDelayMs = DEFAULT_RETRY_DELAY_MS,
    parseResponse = parseJsonResponse<TData>,
    onSuccess,
    onError,
  } = options;

  const [state, setState] = useState<HttpFetchState<TData>>({
    data: null,
    loading: immediate,
    error: null,
    status: null,
    statusText: null,
  });

  const mountedRef = useRef(true);
  const abortControllerRef = useRef<AbortController | null>(null);
  const lastOverridesRef = useRef<Partial<UseHttpFetchOptions<TData, TBody>> | null>(null);

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
      abortControllerRef.current?.abort();
    };
  }, []);

  const execute = useCallback(
    async (overrides: Partial<UseHttpFetchOptions<TData, TBody>> = {}) => {
      lastOverridesRef.current = overrides;

      const requestMethod = overrides.method ?? method;
      const requestHeaders = new Headers(overrides.headers ?? headers);
      const requestBody = overrides.body ?? body;
      const requestQuery = overrides.query ?? query;
      const requestTimeoutMs = overrides.timeoutMs ?? timeoutMs;
      const requestRetries = overrides.retries ?? retries;
      const requestRetryDelayMs = overrides.retryDelayMs ?? retryDelayMs;
      const responseParser = overrides.parseResponse ?? parseResponse;
      const requestUrl = buildUrl(url, requestQuery);

      abortControllerRef.current?.abort();
      const controller = new AbortController();
      abortControllerRef.current = controller;

      if (mountedRef.current) {
        setState((previous) => ({
          ...previous,
          loading: true,
          error: null,
        }));
      }

      const timeoutId = window.setTimeout(() => controller.abort(), requestTimeoutMs);

      try {
        for (let attempt = 0; attempt <= requestRetries; attempt += 1) {
          try {
            const response = await fetch(requestUrl, {
              method: requestMethod,
              headers: requestHeaders,
              body: applyRequestBody(requestHeaders, requestBody),
              signal: controller.signal,
            });

            if (!response.ok) {
              throw new HttpFetchError(response);
            }

            const data = await responseParser(response);

            if (mountedRef.current) {
              setState({
                data,
                loading: false,
                error: null,
                status: response.status,
                statusText: response.statusText,
              });
              onSuccess?.(data);
            }

            return data;
          } catch (error) {
            if (error instanceof Error && error.name === 'AbortError') {
              throw error;
            }

            if (attempt >= requestRetries) {
              throw error;
            }

            await delay(requestRetryDelayMs);
          }
        }
      } catch (error) {
        if (error instanceof Error && error.name === 'AbortError') {
          return null;
        }

        const normalizedError = error instanceof Error ? error : new Error('HTTP request failed');

        if (mountedRef.current) {
          setState({
            data: null,
            loading: false,
            error: normalizedError,
            status: normalizedError instanceof HttpFetchError ? normalizedError.status : null,
            statusText:
              normalizedError instanceof HttpFetchError ? normalizedError.statusText : null,
          });
          onError?.(normalizedError);
        }

        return null;
      } finally {
        window.clearTimeout(timeoutId);
        if (abortControllerRef.current === controller) {
          abortControllerRef.current = null;
        }
      }

      return null;
    },
    [
      body,
      headers,
      method,
      onError,
      onSuccess,
      parseResponse,
      query,
      retries,
      retryDelayMs,
      timeoutMs,
      url,
    ]
  );

  const refetch = useCallback(() => execute(lastOverridesRef.current ?? {}), [execute]);

  const cancel = useCallback(() => {
    abortControllerRef.current?.abort();
  }, []);

  const reset = useCallback(() => {
    abortControllerRef.current?.abort();
    lastOverridesRef.current = null;
    setState({
      data: null,
      loading: false,
      error: null,
      status: null,
      statusText: null,
    });
  }, []);

  useEffect(() => {
    if (immediate) {
      void execute();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [immediate, ...deps]);

  return {
    ...state,
    execute,
    refetch,
    cancel,
    reset,
  };
}

export function useHttpGet<TData = unknown>(
  url: string,
  options: Omit<UseHttpFetchOptions<TData, never>, 'method' | 'body'> = {}
) {
  return useHttpFetch<TData, never>(url, { ...options, method: 'GET' });
}

export function useHttpPost<TData = unknown, TBody = unknown>(
  url: string,
  options: Omit<UseHttpFetchOptions<TData, TBody>, 'method' | 'immediate'> = {}
) {
  return useHttpFetch<TData, TBody>(url, { ...options, method: 'POST', immediate: false });
}

export function useHttpPut<TData = unknown, TBody = unknown>(
  url: string,
  options: Omit<UseHttpFetchOptions<TData, TBody>, 'method' | 'immediate'> = {}
) {
  return useHttpFetch<TData, TBody>(url, { ...options, method: 'PUT', immediate: false });
}

export function useHttpPatch<TData = unknown, TBody = unknown>(
  url: string,
  options: Omit<UseHttpFetchOptions<TData, TBody>, 'method' | 'immediate'> = {}
) {
  return useHttpFetch<TData, TBody>(url, { ...options, method: 'PATCH', immediate: false });
}

export function useHttpDelete<TData = unknown>(
  url: string,
  options: Omit<UseHttpFetchOptions<TData, never>, 'method' | 'body' | 'immediate'> = {}
) {
  return useHttpFetch<TData, never>(url, { ...options, method: 'DELETE', immediate: false });
}
