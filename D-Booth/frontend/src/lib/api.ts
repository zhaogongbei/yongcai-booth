/**
 * Unified API client for D-Booth
 *
 * - Base URL from VITE_API_BASE_URL, defaults to http://localhost:8000/api/v1
 * - Auto attaches Bearer token from tokenStorage (localStorage)
 * - Auto attaches CSRF token on POST/PUT/DELETE/PATCH requests
 * - 401 triggers token refresh; refresh failure dispatches aibooth:unauthorized
 * - 403 CSRF invalidation triggers automatic CSRF token refresh and retry
 * - All fetch requests use credentials: 'include' for CSRF cookie
 *
 * Usage:
 *   import { initCsrfToken, request, tokenStorage, loginForm, ... } from "@/lib/api";
 */

const BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1").replace(/\/$/, "");
// Root URL (without /api/v1) for endpoints outside the API prefix (e.g. /csrf-token)
const ROOT_BASE_URL = BASE_URL.replace(/\/api\/v1$/, "");
const TOKEN_KEY = "aibooth.access_token";
const REFRESH_KEY = "aibooth.refresh_token";

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

interface RequestOptions {
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

export async function request<T = unknown>(path: string, opts: RequestOptions = {}): Promise<T> {
  const { method = "GET", body, query, token: explicitToken, noAuth, skipRefresh, signal } = opts;

  const headers: Record<string, string> = { ...(opts.headers ?? {}) };
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

  let res = await fetch(buildUrl(path, query), {
    method,
    headers,
    body: body !== undefined ? (isFormData ? body : JSON.stringify(body)) : undefined,
    signal,
    credentials: "include",
  });

  // 401 → try token refresh
  if (res.status === 401 && !noAuth && !skipRefresh && tokenStorage.refresh) {
    const refreshed = await refreshTokens();
    if (refreshed) {
      return request<T>(path, { ...opts, skipRefresh: true });
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
    throw new ApiError(res.status, message, data);
  }

  return data as T;
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

// ─── Teams ────────────────────────────────────────────────────────────────────

export interface TeamResponse {
  id: string;
  name: string;
  [key: string]: unknown;
}

export async function getMyTeams(token: string): Promise<TeamResponse[]> {
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

export async function registerBooth(params: {
  teamId: string;
  name: string;
  deviceId: string;
  token: string;
  version?: string;
  ipAddress?: string;
  osInfo?: string;
  currentEventId?: string;
}): Promise<Record<string, unknown>> {
  return request(`/booths/register`, {
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

export async function getTeamBooths(teamId: string, token: string): Promise<Record<string, unknown>[]> {
  return request(`/booths`, { token, query: { team_id: teamId } });
}

export async function getBooth(boothId: string, token: string): Promise<Record<string, unknown>> {
  return request(`/booths/${boothId}`, { token });
}

export async function updateBooth(boothId: string, token: string, data: Record<string, unknown>): Promise<Record<string, unknown>> {
  return request(`/booths/${boothId}`, {
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
