import { useState, createContext, useContext, useCallback } from "react";
import { uploadPhoto, type PhotoResponse } from "../lib/api";

/**
 * Capture flow state: tracks photos taken in the current session,
 * the active event/session context (required for backend upload),
 * and the currently selected photo.
 *
 * Backend integration:
 * - eventId / sessionId are injected by the operator when entering camera mode
 *   (e.g. from EventsScreen "进入拍照" action). Without eventId, capture still
 *   works locally but does NOT persist to the backend.
 * - addPhoto triggers an async upload to POST /api/v1/photos/upload; the local
 *   blob URL is replaced with the persisted photo record once uploaded.
 */

export type MediaType = "photo" | "gif" | "video";

export interface CapturedPhoto {
  id: string;
  url: string;           // blob: URL before upload, persisted URL after
  timestamp: number;
  filter: string;
  mediaType: MediaType;  // 媒体类型：照片/GIF/视频
  serverPhotoId?: string; // set after successful backend upload
  uploaded: boolean;
  uploadError?: string;
}

interface CaptureFlowContextType {
  photos: CapturedPhoto[];
  addPhoto: (photo: { blob?: Blob; url?: string; filter: string; mediaType?: MediaType }) => Promise<void>;
  clearPhotos: () => void;
  selectedPhotoId: string | null;
  setSelectedPhotoId: (id: string | null) => void;
  selectedPhoto: CapturedPhoto | undefined;

  // Event/session context for backend persistence
  eventId: string | null;
  sessionId: string | null;
  currentSessionId: string | null;
  authToken: string | null;
  setCaptureContext: (ctx: { eventId?: string | null; sessionId?: string | null; authToken?: string | null }) => void;
}

const CaptureFlowContext = createContext<CaptureFlowContextType | null>(null);

export function CaptureFlowProvider({ children }: { children: React.ReactNode }) {
  const [photos, setPhotos] = useState<CapturedPhoto[]>([]);
  const [selectedPhotoId, setSelectedPhotoId] = useState<string | null>(null);
  const [eventId, setEventId] = useState<string | null>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [authToken, setAuthToken] = useState<string | null>(null);

  const setCaptureContext = useCallback((ctx: {
    eventId?: string | null; sessionId?: string | null; authToken?: string | null;
  }) => {
    if (ctx.eventId !== undefined) setEventId(ctx.eventId);
    if (ctx.sessionId !== undefined) setSessionId(ctx.sessionId);
    if (ctx.authToken !== undefined) setAuthToken(ctx.authToken);
  }, []);

  const addPhoto = useCallback(async ({ blob, url, filter, mediaType = "photo" }: { blob?: Blob; url?: string; filter: string; mediaType?: MediaType }) => {
    const id = `photo_${Date.now()}`;
    const localUrl = blob ? URL.createObjectURL(blob) : (url ?? "");
    const photo: CapturedPhoto = { id, url: localUrl, timestamp: Date.now(), filter, mediaType, uploaded: false };
    setPhotos(prev => [...prev, photo]);
    setSelectedPhotoId(id);

    // Fire-and-forget backend upload if blob + event context + token are available
    if (blob && eventId && authToken) {
      try {
        const saved: PhotoResponse = await uploadPhoto({ eventId, sessionId: sessionId ?? undefined, file: blob, token: authToken });
        setPhotos(prev => prev.map(p => p.id === id
          ? { ...p, serverPhotoId: saved.id, url: saved.original_url || localUrl, uploaded: true }
          : p));
        // Revoke blob URL after upload (no longer needed)
        if (localUrl.startsWith("blob:")) {
          URL.revokeObjectURL(localUrl);
        }
      } catch (err) {
        setPhotos(prev => prev.map(p => p.id === id
          ? { ...p, uploadError: err instanceof Error ? err.message : "上传失败" }
          : p));
      }
    }
    // No event context / no blob (demo fallback URL): stays local
  }, [eventId, sessionId, authToken]);

  const clearPhotos = useCallback(() => {
    // Revoke blob URLs to prevent memory leaks
    for (const p of photos) {
      if (p.url.startsWith("blob:")) {
        URL.revokeObjectURL(p.url);
      }
    }
    setPhotos([]);
    setSelectedPhotoId(null);
  }, [photos]);

  const selectedPhoto = photos.find(p => p.id === selectedPhotoId);

  return (
    <CaptureFlowContext.Provider value={{
      photos, addPhoto, clearPhotos, selectedPhotoId, setSelectedPhotoId, selectedPhoto,
      eventId, sessionId, currentSessionId: sessionId, authToken, setCaptureContext,
    }}>
      {children}
    </CaptureFlowContext.Provider>
  );
}

export function useCaptureFlow() {
  const ctx = useContext(CaptureFlowContext);
  if (!ctx) throw new Error("useCaptureFlow must be used within CaptureFlowProvider");
  return ctx;
}
