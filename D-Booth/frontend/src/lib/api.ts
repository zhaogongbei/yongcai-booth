/**
 * Unified API client for D-Booth
 *
 * Features:
 * - Base URL from VITE_API_BASE_URL, defaults to http://localhost:8000/api/v1
 * - Auto attaches Bearer token from tokenStorage (localStorage)
 * - Auto attaches CSRF token on POST/PUT/DELETE/PATCH requests
 * - 401 triggers token refresh; refresh failure dispatches aibooth:unauthorized
 * - 403 CSRF invalidation triggers automatic CSRF token refresh and retry
 * - All fetch requests use credentials: 'include' for CSRF cookie
 * - Configurable retry logic for transient failures
 * - Request/response interceptors support
 *
 * Usage:
 *   import { initCsrfToken, request, tokenStorage, loginForm, ... } from "@/lib/api";
 */

const BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1").replace(/\/$/, "");
// Root URL (without /api/v1) for endpoints outside the API prefix (e.g. /csrf-token)
const ROOT_BASE_URL = BASE_URL.replace(/\/api\/v1$/, "");
const TOKEN_KEY = "aibooth.access_token";
const REFRESH_KEY = "aibooth.refresh_token";

// ─── Configuration ────────────────────────────────────────────────────────────

/**
 * Global API configuration
 */
export interface ApiConfig {
  /** Maximum number of retry attempts for failed requests (default: 3) */
  maxRetries: number;
  /** Base delay between retries in milliseconds (default: 1000) */
  retryDelay: number;
  /** HTTP status codes that trigger a retry (default: [408, 429, 500, 502, 503, 504]) */
  retryableStatuses: number[];
  /** Request timeout in milliseconds (default: 30000) */
  timeout: number;
}

let apiConfig: ApiConfig = {
  maxRetries: 3,
  retryDelay: 1000,
  retryableStatuses: [408, 429, 500, 502, 503, 504],
  timeout: 30000,
};

/**
 * Update global API configuration
 *
 * @param config - Partial configuration to merge with defaults
 *
 * @example
 * ```ts
 * setApiConfig({ maxRetries: 5, timeout: 60000 });
 * ```
 */
export function setApiConfig(config: Partial<ApiConfig>): void {
  apiConfig = { ...apiConfig, ...config };
}

/**
 * Get current API configuration
 */
export function getApiConfig(): Readonly<ApiConfig> {
  return { ...apiConfig };
}

// ─── Interceptors ─────────────────────────────────────────────────────────────

type RequestInterceptor = (config: RequestInit, path: string) => RequestInit | Promise<RequestInit>;
type ResponseInterceptor = (response: Response) => Response | Promise<Response>;
type ErrorInterceptor = (error: Error) => Error | Promise<Error>;

const requestInterceptors: RequestInterceptor[] = [];
const responseInterceptors: ResponseInterceptor[] = [];
const errorInterceptors: ErrorInterceptor[] = [];

/**
 * Add a request interceptor
 *
 * @param interceptor - Function to modify request config before sending
 * @returns Function to remove the interceptor
 *
 * @example
 * ```ts
 * const removeInterceptor = addRequestInterceptor((config, path) => {
 *   console.log('Sending request to:', path);
 *   return config;
 * });
 *
 * // Later: removeInterceptor();
 * ```
 */
export function addRequestInterceptor(interceptor: RequestInterceptor): () => void {
  requestInterceptors.push(interceptor);
  return () => {
    const index = requestInterceptors.indexOf(interceptor);
    if (index > -1) requestInterceptors.splice(index, 1);
  };
}

/**
 * Add a response interceptor
 *
 * @param interceptor - Function to process response before parsing
 * @returns Function to remove the interceptor
 */
export function addResponseInterceptor(interceptor: ResponseInterceptor): () => void {
  responseInterceptors.push(interceptor);
  return () => {
    const index = responseInterceptors.indexOf(interceptor);
    if (index > -1) responseInterceptors.splice(index, 1);
  };
}

/**
 * Add an error interceptor
 *
 * @param interceptor - Function to process errors before throwing
 * @returns Function to remove the interceptor
 */
export function addErrorInterceptor(interceptor: ErrorInterceptor): () => void {
  errorInterceptors.push(interceptor);
  return () => {
    const index = errorInterceptors.indexOf(interceptor);
    if (index > -1) errorInterceptors.splice(index, 1);
  };
}

// ─── Token Storage ────────────────────────────────────────────────────────────

export const tokenStorage = {
  get access(): string | null {
    return localStorage.getItem(TOKEN_KEY);
  },
  get refresh(): string | null {
    return localStorage.getItem(REFRESH_KEY);
  },
  set(access: string, refresh?: string) {
    localStorage.setItem(TOKEN_KEY, access);
    if (refresh) localStorage.setItem(REFRESH_KEY, refresh);
  },
  clear() {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(REFRESH_KEY);
  },
};

// ─── CSRF Token ───────────────────────────────────────────────────────────────

let csrfToken: string | null = null;

export async function initCsrfToken(): Promise<void> {
  try {
    const response = await fetch(`${ROOT_BASE_URL}/csrf-token`, {
      credentials: "include",
    });
    const data = await response.json();
    csrfToken = data.csrf_token;
  } catch (error) {
    console.error("Failed to initialize CSRF token:", error);
    // Don't throw - allow app to continue (read-only operations still work)
  }
}

// ─── ApiError ─────────────────────────────────────────────────────────────────

export class ApiError extends Error {
  constructor(public status: number, message: string, public data?: unknown) {
    super(message);
    this.name = "ApiError";
  }
}

// ─── Request ──────────────────────────────────────────────────────────────────

type RequestMethod = "GET" | "POST" | "PUT" | "PATCH" | "DELETE";

export interface RequestOptions {
  method?: RequestMethod;
  body?: unknown;
  headers?: Record<string, string>;
  query?: Record<string, string | number | boolean | undefined | null>;
  /** Explicit token override — when provided, this is used instead of tokenStorage.access */
  token?: string;
  /** When true, Authorization header is omitted (for login, refresh, register) */
  noAuth?: boolean;
  /** When true, skip the automatic token refresh flow on 401 */
  skipRefresh?: boolean;
  /** Request timeout in milliseconds (overrides global config) */
  timeout?: number;
  /** Maximum retry attempts (overrides global config) */
  maxRetries?: number;
  /** Whether to retry this specific request on failure (default: true) */
  retry?: boolean;
  signal?: AbortSignal;
}

function buildUrl(path: string, query?: RequestOptions["query"]): string {
  const url = path.startsWith("http") ? path : `${BASE_URL}${path.startsWith("/") ? "" : "/"}${path}`;
  if (!query) return url;
  const params = new URLSearchParams();
  for (const [k, v] of Object.entries(query)) {
    if (v !== undefined && v !== null) params.append(k, String(v));
  }
  const qs = params.toString();
  return qs ? `${url}?${qs}` : url;
}

/**
 * Sleep helper for retry delays
 */
function sleep(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms));
}

/**
 * Calculate exponential backoff delay
 */
function getRetryDelay(attempt: number, baseDelay: number): number {
  return baseDelay * Math.pow(2, attempt) + Math.random() * 1000;
}

function createAbortError(): Error {
  const error = new Error("The operation was aborted.");
  error.name = "AbortError";
  return error;
}

function isAbortError(error: unknown): error is Error {
  return error instanceof Error && error.name === "AbortError";
}

export async function request<T = unknown>(path: string, opts: RequestOptions = {}): Promise<T> {
  const {
    method = "GET",
    body,
    query,
    token: explicitToken,
    noAuth,
    skipRefresh,
    timeout = apiConfig.timeout,
    maxRetries = apiConfig.maxRetries,
    retry = true,
    signal,
  } = opts;

  let lastError: Error | null = null;
  const attemptLimit = retry ? maxRetries + 1 : 1;

  for (let attempt = 0; attempt < attemptLimit; attempt++) {
    try {
      // Apply request interceptors
      let requestConfig: RequestInit = {
        method,
        headers: { ...(opts.headers ?? {}) },
        credentials: "include",
      };

      for (const interceptor of requestInterceptors) {
        requestConfig = await interceptor(requestConfig, path);
      }

      const headers: Record<string, string> = { ...(requestConfig.headers as Record<string, string>) };
      const isFormData = typeof FormData !== "undefined" && body instanceof FormData;

      if (body !== undefined && !isFormData && !headers["Content-Type"]) {
        headers["Content-Type"] = "application/json";
      }

      // Attach Bearer token — explicitToken takes precedence over tokenStorage
      if (!noAuth) {
        const token = explicitToken ?? tokenStorage.access;
        if (token) headers["Authorization"] = `Bearer ${token}`;
      }

      // Attach CSRF token for state-changing requests
      if (["POST", "PUT", "DELETE", "PATCH"].includes(method) && csrfToken) {
        headers["X-CSRF-Token"] = csrfToken;
      }

      if (signal?.aborted) {
        throw createAbortError();
      }

      // Setup timeout and forward caller cancellation into one fetch signal.
      const controller = new AbortController();
      let didTimeout = false;
      const abortFromCaller = () => controller.abort();
      signal?.addEventListener("abort", abortFromCaller, { once: true });
      const timeoutId = setTimeout(() => {
        didTimeout = true;
        controller.abort();
      }, timeout);

      try {
        let res = await fetch(buildUrl(path, query), {
          ...requestConfig,
          method,
          headers,
          body: body !== undefined ? (isFormData ? body : JSON.stringify(body)) : undefined,
          signal: controller.signal,
        });

        clearTimeout(timeoutId);
        signal?.removeEventListener("abort", abortFromCaller);

        // Apply response interceptors
        for (const interceptor of responseInterceptors) {
          res = await interceptor(res);
        }

        // 401 → try token refresh
        if (res.status === 401 && !noAuth && !skipRefresh && tokenStorage.refresh) {
          const refreshed = await refreshTokens();
          if (refreshed) {
            // Drop any explicit stale access token so the retried request can use
            // the freshly refreshed token from tokenStorage.
            return request<T>(path, { ...opts, token: undefined, skipRefresh: true });
          }
        }

        // 403 CSRF invalidation → refresh CSRF and retry
        if (res.status === 403) {
          try {
            const errorBody = await res.clone().json();
            if (errorBody.detail === "CSRF token validation failed") {
              await initCsrfToken();
              return request<T>(path, opts);
            }
          } catch {
            // Not a CSRF error - continue to normal error handling
          }
        }

        const text = await res.text();
        const data: unknown = text ? JSON.parse(text) : null;

        if (!res.ok) {
          if (res.status === 401) {
            tokenStorage.clear();
            window.dispatchEvent(new CustomEvent("aibooth:unauthorized"));
          }

          const message: string =
            (data && typeof data === "object" && typeof (data as Record<string, unknown>).detail === "string"
              ? (data as Record<string, string>).detail
              : undefined) ||
            (data && typeof data === "object" && typeof (data as Record<string, unknown>).message === "string"
              ? (data as Record<string, string>).message
              : undefined) ||
            res.statusText;

          const error = new ApiError(res.status, message, data);

          // Check if this error is retryable
          if (retry && attempt < maxRetries && apiConfig.retryableStatuses.includes(res.status)) {
            lastError = error;
            const delay = getRetryDelay(attempt, apiConfig.retryDelay);
            await sleep(delay);
            continue;
          }

          throw error;
        }

        return data as T;
      } catch (err) {
        clearTimeout(timeoutId);
        signal?.removeEventListener("abort", abortFromCaller);

        if (isAbortError(err) && !didTimeout && signal?.aborted) {
          throw err;
        }

        if (isAbortError(err)) {
          const timeoutError = new Error(`Request timeout after ${timeout}ms`);
          lastError = timeoutError;

          if (retry && attempt < maxRetries) {
            const delay = getRetryDelay(attempt, apiConfig.retryDelay);
            await sleep(delay);
            continue;
          }

          // Apply error interceptors
          let processedError: Error = timeoutError;
          for (const interceptor of errorInterceptors) {
            processedError = await interceptor(processedError);
          }
          throw processedError;
        }

        throw err;
      }
    } catch (err) {
      const error = err instanceof Error ? err : new Error('Unknown error');
      lastError = error;

      // Don't retry on non-retryable errors
      if (!retry || attempt >= maxRetries || !(error instanceof ApiError)) {
        // Apply error interceptors
        let processedError = error;
        for (const interceptor of errorInterceptors) {
          processedError = await interceptor(processedError);
        }
        throw processedError;
      }

      // Wait before retry
      const delay = getRetryDelay(attempt, apiConfig.retryDelay);
      await sleep(delay);
    }
  }

  // This should never be reached, but TypeScript needs it
  throw lastError || new Error('Request failed');
}

export interface BackendHealthResponse {
  status: "healthy" | "degraded" | string;
  version?: string;
  components?: Record<string, string>;
}

export async function getBackendHealth(): Promise<BackendHealthResponse> {
  const response = await fetch(`${ROOT_BASE_URL}/health`, {
    credentials: "include",
  });
  const text = await response.text();
  const data = text ? JSON.parse(text) : null;
  if (!response.ok) {
    throw new ApiError(response.status, data?.detail || response.statusText, data);
  }
  return data as BackendHealthResponse;
}

export function resolveBackendUrl(path: string): string {
  if (/^https?:\/\//i.test(path)) return path;
  if (path.startsWith("/uploads/green-screen/")) {
    return `${BASE_URL}/green-screen/assets/${path.slice("/uploads/green-screen/".length)}`;
  }
  return `${ROOT_BASE_URL}${path.startsWith("/") ? "" : "/"}${path}`;
}

async function refreshTokens(): Promise<boolean> {
  const refreshToken = tokenStorage.refresh;
  if (!refreshToken) return false;

  try {
    const tokens = await request<{ access_token: string; refresh_token: string }>(
      "/auth/refresh",
      {
        method: "POST",
        body: { refresh_token: refreshToken },
        noAuth: true,
        skipRefresh: true,
      }
    );
    tokenStorage.set(tokens.access_token, tokens.refresh_token);
    return true;
  } catch {
    tokenStorage.clear();
    window.dispatchEvent(new CustomEvent("aibooth:unauthorized"));
    return false;
  }
}

// ─── Auth ─────────────────────────────────────────────────────────────────────

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

/** OAuth2 password form login (application/x-www-form-urlencoded) */
export async function loginForm(username: string, password: string): Promise<LoginResponse> {
  const form = new URLSearchParams();
  form.set("username", username);
  form.set("password", password);
  const res = await fetch(`${BASE_URL}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: form.toString(),
    credentials: "include",
  });
  const text = await res.text();
  const data = text ? JSON.parse(text) : null;
  if (!res.ok) throw new ApiError(res.status, data?.detail || res.statusText, data);
  return data;
}

/** Legacy login alias (same as loginForm, kept for backward compatibility) */
export const login = loginForm;

// ─── Photos ───────────────────────────────────────────────────────────────────

export interface PhotoUploadParams {
  eventId: string;
  sessionId?: string;
  file: Blob;
  token: string;
}

export interface PhotoResponse {
  id: string;
  event_id: string;
  session_id?: string;
  original_url: string;
  thumbnail_url?: string;
  file_size?: number;
  width?: number;
  height?: number;
  created_at: string;
  updated_at: string;
}

export interface PhotoSessionResponse {
  id: string;
  event_id: string;
  email?: string;
  phone?: string;
  started_at: string;
  completed_at?: string;
  created_at: string;
  updated_at: string;
}

export async function createPhotoSession(params: {
  eventId: string;
  token: string;
  email?: string;
  phone?: string;
}): Promise<PhotoSessionResponse> {
  return request<PhotoSessionResponse>("/photos/sessions", {
    method: "POST",
    token: params.token,
    body: {
      event_id: params.eventId,
      email: params.email,
      phone: params.phone,
    },
  });
}

export async function uploadPhoto(params: PhotoUploadParams): Promise<PhotoResponse> {
  const formData = new FormData();
  formData.append("file", params.file, "capture.jpg");

  const url = new URL("/api/v1/photos/upload", BASE_URL);
  url.searchParams.set("event_id", params.eventId);
  if (params.sessionId) {
    url.searchParams.set("session_id", params.sessionId);
  }

  const response = await fetch(url.toString(), {
    method: "POST",
    headers: {
      Authorization: `Bearer ${params.token}`,
    },
    body: formData,
    credentials: "include",
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail || `Upload failed: ${response.status}`);
  }

  return response.json();
}

// ─── Print Jobs ───────────────────────────────────────────────────────────────

export interface PrintJobCreateParams {
  photoId: string;
  printerName?: string;
  copies?: number;
  token: string;
}

export interface PrintJobResponse {
  id: string;
  photo_id: string;
  status: "pending" | "queued" | "printing" | "completed" | "failed" | "cancelled";
  printer_name?: string;
  copies: number;
  error_message?: string;
  printed_at?: string;
  created_at: string;
  updated_at: string;
}

export async function createPrintJob(params: PrintJobCreateParams): Promise<PrintJobResponse> {
  return request<PrintJobResponse>("/print-jobs", {
    method: "POST",
    token: params.token,
    body: {
      photo_id: params.photoId,
      printer_name: params.printerName,
      copies: params.copies || 1,
    },
  });
}

export async function getPrintJob(jobId: string, token: string): Promise<PrintJobResponse> {
  return request<PrintJobResponse>(`/print-jobs/${jobId}`, { token });
}

export async function retryPrintJob(jobId: string, token: string): Promise<PrintJobResponse> {
  return request<PrintJobResponse>(`/print-jobs/${jobId}/retry`, {
    method: "POST",
    token,
  });
}

export async function cancelPrintJob(jobId: string, token: string): Promise<void> {
  await request<void>(`/print-jobs/${jobId}`, {
    method: "DELETE",
    token,
  });
}

// ─── Events ───────────────────────────────────────────────────────────────────

export interface EventResponse {
  id: string;
  team_id: string;
  creator_id: string;
  name: string;
  description?: string;
  event_type?: string;
  status: "draft" | "scheduled" | "active" | "completed" | "cancelled";
  start_date: string;
  end_date: string;
  venue_name?: string;
  venue_address?: string;
  created_at: string;
  updated_at: string;
}

export async function getEvents(token: string, teamId?: string): Promise<EventResponse[]> {
  const query: Record<string, string> = {};
  if (teamId) query.team_id = teamId;
  return request<EventResponse[]>("/events", { token, query })
    .catch(() => request<EventResponse[]>("/events", { token }));
}

// ─── Shares ───────────────────────────────────────────────────────────────────

export interface ShareCreateParams {
  photoId: string;
  channel: string;
  recipient?: string;
  token: string;
}

export interface ShareResponse {
  id: string;
  photo_id: string;
  channel: string;
  recipient?: string;
  short_code: string;
  full_url: string;
  view_count: number;
  expires_at: string;
  created_at: string;
  updated_at: string;
}

export async function createShare(params: ShareCreateParams): Promise<ShareResponse> {
  return request<ShareResponse>("/shares", {
    method: "POST",
    token: params.token,
    body: {
      photo_id: params.photoId,
      channel: params.channel,
      recipient: params.recipient,
    },
  });
}

// ─── Analytics ────────────────────────────────────────────────────────────────

export interface AnalyticsOverview {
  total_events?: number;
  total_photos?: number;
  total_prints?: number;
  total_shares?: number;
  active_events?: number;
  estimated_revenue?: number;
  revenue?: number;
  unique_users?: number;
  unique_sessions?: number;
  events_by_type?: Record<string, number>;
  [key: string]: unknown;
}

export async function getAnalyticsOverview(teamId: string, token: string): Promise<AnalyticsOverview> {
  return request<AnalyticsOverview>("/analytics/overview", { token, query: { team_id: teamId } })
    .catch(() => ({}));
}

// ─── Beauty ───────────────────────────────────────────────────────────────────

export interface BeautyParams {
  smooth: number;
  whiten: number;
  thinFace: number;
  bigEye: number;
  eyeLight: number;
  acne: number;
  nasolabial: number;
  teethWhiten: number;
  lipColor: number;
}

export interface BeautyPreset {
  name: string;
  params: BeautyParams;
}

export interface FaceBox {
  x: number;
  y: number;
  width: number;
  height: number;
  confidence: number;
  landmark_count: number;
}

export interface FaceDetectionResponse {
  face_count: number;
  faces: FaceBox[];
}

export async function getBeautyPresets(): Promise<BeautyPreset[]> {
  return request<BeautyPreset[]>("/beauty/presets");
}

export async function detectFace(image: Blob, token?: string): Promise<FaceDetectionResponse> {
  const formData = new FormData();
  formData.append("file", image, "photo.jpg");

  const headers: Record<string, string> = {};
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(`${BASE_URL}/beauty/detect-face`, {
    method: "POST",
    headers,
    body: formData,
    credentials: "include",
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail || `Face detection failed: ${res.status}`);
  }

  return res.json();
}

export async function processBeautyImage(image: Blob, params: BeautyParams, signal?: AbortSignal, token?: string): Promise<Blob> {
  const formData = new FormData();
  formData.append("file", image, "photo.jpg");
  formData.append("smooth", params.smooth.toString());
  formData.append("whiten", params.whiten.toString());
  formData.append("thinFace", params.thinFace.toString());
  formData.append("bigEye", params.bigEye.toString());
  formData.append("eyeLight", params.eyeLight.toString());
  formData.append("acne", params.acne.toString());
  formData.append("nasolabial", params.nasolabial.toString());
  formData.append("teethWhiten", params.teethWhiten.toString());
  formData.append("lipColor", params.lipColor.toString());

  const headers: Record<string, string> = {};
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(`${BASE_URL}/beauty/preview`, {
    method: "POST",
    headers,
    body: formData,
    credentials: "include",
    signal,
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail || `Beauty processing failed: ${res.status}`);
  }

  return res.blob();
}

// ─── Templates ────────────────────────────────────────────────────────────────

export interface TemplatePayload {
  name: string;
  description?: string | null;
  size?: string | null;
  canvas_width?: number | null;
  canvas_height?: number | null;
  layers?: Record<string, unknown> | null;
  thumbnail_url?: string | null;
  is_public?: boolean;
}

export interface TemplateCreatePayload extends TemplatePayload {
  team_id: string;
}

export type TemplateUpdatePayload = Partial<TemplatePayload>;

export interface TemplateResponse {
  id: string;
  team_id: string;
  name: string;
  description?: string | null;
  size?: string | null;
  canvas_width?: string | number | null;
  canvas_height?: string | number | null;
  layers?: Record<string, unknown> | null;
  thumbnail_url?: string | null;
  is_public: boolean;
  created_at: string;
  updated_at: string;
}

export async function getTemplates(teamId: string, token?: string): Promise<TemplateResponse[]> {
  return request<TemplateResponse[]>("/templates", {
    token,
    query: { team_id: teamId },
  });
}

export async function getTemplate(templateId: string, token?: string): Promise<TemplateResponse> {
  return request<TemplateResponse>(`/templates/${templateId}`, { token });
}

export async function createTemplate(payload: TemplateCreatePayload, token?: string): Promise<TemplateResponse> {
  return request<TemplateResponse>("/templates", {
    method: "POST",
    token,
    body: payload,
  });
}

export async function updateTemplate(
  templateId: string,
  payload: TemplateUpdatePayload,
  token?: string
): Promise<TemplateResponse> {
  return request<TemplateResponse>(`/templates/${templateId}`, {
    method: "PUT",
    token,
    body: payload,
  });
}

export async function deleteTemplate(templateId: string, token?: string): Promise<void> {
  await request<void>(`/templates/${templateId}`, {
    method: "DELETE",
    token,
  });
}

export async function duplicateTemplate(templateId: string, newName?: string, token?: string): Promise<TemplateResponse> {
  return request<TemplateResponse>(`/templates/${templateId}/duplicate`, {
    method: "POST",
    token,
    body: { new_name: newName },
  });
}

export async function validateTemplate(templateData: Record<string, unknown>, token?: string): Promise<{ valid: boolean; message: string }> {
  return request<{ valid: boolean; message: string }>("/templates/validate", {
    method: "POST",
    token,
    body: { template_data: templateData },
  });
}

// ─── Teams ────────────────────────────────────────────────────────────────────

export interface TeamResponse {
  id: string;
  name: string;
  [key: string]: unknown;
}

export async function getMyTeams(token?: string): Promise<TeamResponse[]> {
  return request<TeamResponse[]>("/teams", { token }).catch(() => []);
}

// ─── Share Settings ────────────────────────────────────────────────────────────

export interface WiFiSettings {
  ssid: string;
  password: string;
  encryption: string;
}

export interface SMTPSettings {
  host: string;
  port: number;
  user: string;
  password: string;
  from_email: string;
  use_tls: boolean;
}

export interface TwilioSettings {
  account_sid: string;
  auth_token: string;
  from_number: string;
}

export interface TemplateSettings {
  email_subject: string;
  email_body: string;
  sms_message: string;
}

export interface ShareSettings {
  enabled_channels: string[];
  wifi: WiFiSettings;
  smtp: SMTPSettings;
  twilio: TwilioSettings;
  templates: TemplateSettings;
  whatsapp_number: string;
}

export interface ShareSettingsResponse extends ShareSettings {
  event_id: string;
}

export async function getShareSettings(eventId: string, token: string): Promise<ShareSettings> {
  return request<ShareSettingsResponse>(`/settings/sharing/${eventId}`, { token });
}

export async function updateShareSettings(eventId: string, settings: ShareSettings, token: string): Promise<ShareSettingsResponse> {
  return request<ShareSettingsResponse>(`/settings/sharing/${eventId}`, {
    method: "PUT",
    token,
    body: settings,
  });
}

// ─── Share Send Operations ─────────────────────────────────────────────────────

export interface SendEmailParams {
  toEmail: string;
  eventId: string;
  photoUrls: string[];
  shareUrl: string;
  token: string;
}

export interface SendSMSParams {
  toPhone: string;
  eventId: string;
  shareUrl: string;
  countryCode: string;
  token: string;
}

export async function sendShareEmail(params: SendEmailParams): Promise<{ status: string; message: string }> {
  return request<{ status: string; message: string }>("/shares/email/test", {
    method: "POST",
    token: params.token,
    body: {
      to_email: params.toEmail,
      event_id: params.eventId,
      photo_urls: params.photoUrls,
      share_url: params.shareUrl,
    },
  });
}

export async function sendShareSMS(params: SendSMSParams): Promise<{ status: string; message: string }> {
  return request<{ status: string; message: string }>("/shares/sms/test", {
    method: "POST",
    token: params.token,
    body: {
      to_phone: params.toPhone,
      event_id: params.eventId,
      share_url: params.shareUrl,
      country_code: params.countryCode,
    },
  });
}

// ─── Virtual Attendant ────────────────────────────────────────────────────────

export interface VirtualAttendantPlaylistItem {
  timing: string;
  enabled: boolean;
  text: string;
  language: string;
  voice: string;
}

export async function getVirtualAttendantPlaylist(
  eventId: string
): Promise<VirtualAttendantPlaylistItem[]> {
  return request<VirtualAttendantPlaylistItem[]>(`/virtual-attendant/playlist/${eventId}`);
}

export function getVirtualAttendantTtsUrl(params: {
  timing: string;
  eventId: string;
  language: string;
  voice: string;
}): string {
  const url = new URL(`${BASE_URL}/virtual-attendant/tts/${encodeURIComponent(params.timing)}`);
  url.searchParams.set("event_id", params.eventId);
  url.searchParams.set("language", params.language);
  url.searchParams.set("voice", params.voice);
  return url.toString();
}

export async function previewVirtualAttendantTts(params: {
  text: string;
  language: string;
  voice: string;
}): Promise<Blob> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  const token = tokenStorage.access;
  if (token) headers.Authorization = `Bearer ${token}`;

  const response = await fetch(`${BASE_URL}/virtual-attendant/preview`, {
    method: "POST",
    headers,
    credentials: "include",
    body: JSON.stringify(params),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new ApiError(response.status, error.detail || response.statusText, error);
  }

  return response.blob();
}

// ─── Green Screen ─────────────────────────────────────────────────────────────

export type GreenScreenMode = "chroma_key" | "ai_removal" | "auto";
export type GreenScreenBackgroundMode = "rotate" | "manual";
export type GreenScreenOutputSize = "template" | "1800x1200" | "max";

export interface GreenScreenBackgroundResponse {
  id: string;
  name: string;
  background_url: string;
  overlay_url?: string | null;
  order: number;
  created_at: string;
}

export interface GreenScreenSettingsPayload {
  enabled: boolean;
  mode: GreenScreenMode;
  color_to_remove: string;
  sensitivity: number;
  smoothness: number;
  use_flash: boolean;
  background_mode: GreenScreenBackgroundMode;
  output_size: GreenScreenOutputSize;
  current_background_index: number;
}

export interface GreenScreenSettingsResponse extends GreenScreenSettingsPayload {
  id: string;
  event_id: string;
  backgrounds: GreenScreenBackgroundResponse[];
  created_at: string;
  updated_at: string;
}

export interface GreenScreenAnalysisResponse {
  complexity_score: number;
  recommended_mode: GreenScreenMode;
  is_green_background: boolean;
  suggested_sensitivity: number;
  suggestions: string[];
}

export async function getGreenScreenSettings(eventId: string): Promise<GreenScreenSettingsResponse> {
  return request<GreenScreenSettingsResponse>(`/green-screen/settings/${eventId}`);
}

export async function updateGreenScreenSettings(
  eventId: string,
  settings: GreenScreenSettingsPayload
): Promise<GreenScreenSettingsResponse> {
  return request<GreenScreenSettingsResponse>(`/green-screen/settings/${eventId}`, {
    method: "PUT",
    body: settings,
  });
}

export async function uploadGreenScreenBackground(
  eventId: string,
  file: File,
  name: string,
  overlayFile?: File
): Promise<GreenScreenBackgroundResponse> {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("name", name);
  formData.append("event_id", eventId);
  if (overlayFile) {
    formData.append("overlay_file", overlayFile);
  }

  return request<GreenScreenBackgroundResponse>("/green-screen/backgrounds", {
    method: "POST",
    body: formData,
  });
}

export async function deleteGreenScreenBackground(
  eventId: string,
  backgroundId: string
): Promise<{ success: boolean }> {
  return request<{ success: boolean }>(`/green-screen/backgrounds/${backgroundId}`, {
    method: "DELETE",
    query: { event_id: eventId },
  });
}

export async function previewGreenScreenImage(
  image: Blob,
  settings: GreenScreenSettingsPayload,
  background?: Blob,
  signal?: AbortSignal
): Promise<Blob> {
  const formData = new FormData();
  formData.append("file", image, "test.jpg");
  formData.append("settings", JSON.stringify(settings));
  if (background) {
    formData.append("background_file", background, "background.jpg");
  }
  const headers: Record<string, string> = {};
  const token = tokenStorage.access;
  if (token) headers.Authorization = `Bearer ${token}`;

  const response = await fetch(`${BASE_URL}/green-screen/preview`, {
    method: "POST",
    headers,
    body: formData,
    credentials: "include",
    signal,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new ApiError(response.status, error.detail || response.statusText, error);
  }

  return response.blob();
}

export async function analyzeGreenScreenTestPhoto(
  image: Blob
): Promise<GreenScreenAnalysisResponse> {
  const formData = new FormData();
  formData.append("file", image, "test.jpg");
  const headers: Record<string, string> = {};
  const token = tokenStorage.access;
  if (token) headers.Authorization = `Bearer ${token}`;

  const response = await fetch(`${BASE_URL}/green-screen/test-photo`, {
    method: "POST",
    headers,
    body: formData,
    credentials: "include",
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new ApiError(response.status, error.detail || response.statusText, error);
  }

  return response.json();
}

// ─── Printers ──────────────────────────────────────────────────────────────────

export interface PrinterInfo {
  name: string;
  status: "ready" | "offline" | "paper_out" | "ink_low" | "error";
  is_default: boolean;
  location?: string;
  driver_name?: string;
  port_name?: string;
}

export interface PrintQueueItem {
  job_id: number;
  document: string;
  user: string;
  status: string;
  pages_total: number;
  pages_printed: number;
  submitted_time: string;
}

export interface CalibrationParams {
  scale: number;
  offset_x: number;
  offset_y: number;
  rotation: number;
}

export async function getPrinters(): Promise<PrinterInfo[]> {
  return request<PrinterInfo[]>("/printers");
}

export async function getPrinterStatus(printerName: string): Promise<string> {
  return request<string>(`/printers/${encodeURIComponent(printerName)}/status`);
}

export async function getPrintQueue(printerName: string): Promise<PrintQueueItem[]> {
  return request<PrintQueueItem[]>(`/printers/${encodeURIComponent(printerName)}/queue`);
}

export async function printTestPage(printerName: string): Promise<{ success: boolean; message: string }> {
  return request<{ success: boolean; message: string }>(`/printers/${encodeURIComponent(printerName)}/test-page`, {
    method: "POST",
  });
}

export async function saveCalibration(printerName: string, params: CalibrationParams): Promise<{ success: boolean; message: string }> {
  return request<{ success: boolean; message: string }>(`/printers/${encodeURIComponent(printerName)}/calibration`, {
    method: "PUT",
    body: params,
  });
}

export async function cancelPrintQueueJob(printerName: string, jobId: number): Promise<{ success: boolean }> {
  return request<{ success: boolean }>(`/printers/${encodeURIComponent(printerName)}/queue/${jobId}`, {
    method: "DELETE",
  });
}

// ─── Booth Health ─────────────────────────────────────────────────────────────

export interface CameraHealthResponse {
  connected: boolean;
  model?: string | null;
  controller_type?: string | null;
  battery_level?: number | null;
  storage_remaining?: number | null;
  error?: string | null;
}

export interface BoothHealthResponse {
  overall: "ok" | "warn" | "error" | "idle" | string;
  ready: boolean;
  issues: string[];
  api: {
    online: boolean;
    status: "healthy" | "degraded" | "offline" | "unknown" | string;
    error?: string | null;
  };
  camera: CameraHealthResponse;
  printers: PrinterInfo[];
  selected_printer?: PrinterInfo | null;
  print_queue: PrintQueueItem[];
  queue: {
    total: number;
    active: number;
    blocked: number;
  };
  timestamp: string;
}

export async function getBoothHealth(): Promise<BoothHealthResponse> {
  return request<BoothHealthResponse>("/booth/health");
}

// ─── Booths ────────────────────────────────────────────────────────────────────

export interface BoothResponse {
  id: string;
  team_id: string;
  name: string;
  device_id: string;
  status: "online" | "offline" | "busy" | "error";
  version?: string | null;
  last_heartbeat?: string | null;
  ip_address?: string | null;
  os_info?: string | null;
  current_event_id?: string | null;
  config_hash?: string | null;
  created_at: string;
  updated_at: string;
}

export async function registerBooth(params: {
  teamId: string;
  name: string;
  deviceId: string;
  token: string;
  version?: string;
  ipAddress?: string;
  osInfo?: string;
  currentEventId?: string;
}): Promise<BoothResponse> {
  return request<BoothResponse>(`/booths/register`, {
    method: "POST",
    token: params.token,
    body: {
      team_id: params.teamId,
      name: params.name,
      device_id: params.deviceId,
      version: params.version,
      ip_address: params.ipAddress,
      os_info: params.osInfo,
      current_event_id: params.currentEventId,
    },
  });
}

export async function boothHeartbeat(boothId: string, token: string): Promise<Record<string, unknown>> {
  return request(`/booths/${boothId}/heartbeat`, {
    method: "POST",
    token,
  });
}

export async function getTeamBooths(teamId: string, token: string): Promise<BoothResponse[]> {
  return request<BoothResponse[]>(`/booths`, { token, query: { team_id: teamId } });
}

export async function getBooth(boothId: string, token: string): Promise<BoothResponse> {
  return request<BoothResponse>(`/booths/${boothId}`, { token });
}

export async function updateBooth(boothId: string, token: string, data: Record<string, unknown>): Promise<BoothResponse> {
  return request<BoothResponse>(`/booths/${boothId}`, {
    method: "PUT",
    token,
    body: data,
  });
}

export async function deregisterBooth(boothId: string, token: string): Promise<Record<string, unknown>> {
  return request(`/booths/${boothId}`, {
    method: "DELETE",
    token,
  });
}

// ─── Sync ──────────────────────────────────────────────────────────────────────

export async function getSyncState(boothId: string, teamId: string, token: string): Promise<Record<string, unknown>> {
  return request(`/sync/state/${boothId}`, { token, query: { team_id: teamId } });
}

export async function pushConfig(boothId: string, teamId: string, token: string): Promise<Record<string, unknown>> {
  return request(`/sync/push/${boothId}`, {
    method: "POST",
    token,
    query: { team_id: teamId },
  });
}

export async function pullConfig(boothId: string, teamId: string, token: string): Promise<Record<string, unknown>> {
  return request(`/sync/pull/${boothId}`, {
    method: "POST",
    token,
    query: { team_id: teamId },
  });
}

export async function getSyncLog(teamId: string, token: string): Promise<Record<string, unknown>> {
  return request(`/sync/log/${teamId}`, { token });
}
