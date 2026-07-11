import { useState, useCallback, useEffect, useMemo } from "react";
import { ArrowDownWideNarrow, ArrowUpNarrowWide, CalendarDays, Download, Eye, ImageOff, RefreshCw, X } from "lucide-react";
import { motion, AnimatePresence } from "motion/react";
import { toast } from "sonner";
import { GlassCard } from "../components/GlassCard";
import { GlowBtn } from "../components/GlowBtn";
import { getPhotos, resolveBackendUrl, tokenStorage, type PhotoResponse } from "../../lib/api";
import { useSettings } from "../stores/useSettings";
import { useCaptureFlow } from "../stores/useCaptureFlow";
import type { Screen } from "../types";

interface GalleryScreenProps {
  navigate?: (s: Screen) => void;
}

export function GalleryScreen({ navigate }: GalleryScreenProps) {
  const { currentEvent } = useSettings();
  const captureFlow = useCaptureFlow();
  const eventId = currentEvent?.id ?? captureFlow.eventId;
  const isLoggedIn = Boolean(tokenStorage.access);

  const [photos, setPhotos] = useState<PhotoResponse[]>([]);
  const [loading, setLoading] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [latestFirst, setLatestFirst] = useState(true);
  const [previewPhoto, setPreviewPhoto] = useState<PhotoResponse | null>(null);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());

  const loadPhotos = useCallback(async () => {
    if (!eventId || !isLoggedIn) return;
    setLoading(true);
    setLoadError(null);
    try {
      const result = await getPhotos({ eventId });
      setPhotos(result);
      setSelectedIds(new Set());
    } catch (err) {
      setLoadError(err instanceof Error ? err.message : "照片加载失败");
    } finally {
      setLoading(false);
    }
  }, [eventId, isLoggedIn]);

  useEffect(() => {
    void loadPhotos();
  }, [loadPhotos]);

  const sortedPhotos = useMemo(() => {
    const list = [...photos].sort(
      (a, b) => Date.parse(a.created_at) - Date.parse(b.created_at),
    );
    return latestFirst ? list.reverse() : list;
  }, [photos, latestFirst]);

  const togglePhoto = (id: string) => {
    setSelectedIds(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const downloadPhoto = useCallback(async (photo: PhotoResponse) => {
    const url = resolveBackendUrl(photo.original_url);
    const response = await fetch(url, { credentials: "include" });
    if (!response.ok) {
      throw new Error(`下载失败（${response.status}）`);
    }
    const blob = await response.blob();
    const objectUrl = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = objectUrl;
    link.download = `photo-${photo.id}.jpg`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(objectUrl);
  }, []);

  const handleDownload = useCallback(async (photo: PhotoResponse, e?: React.MouseEvent) => {
    e?.stopPropagation();
    try {
      await downloadPhoto(photo);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "下载失败");
    }
  }, [downloadPhoto]);

  const handleBatchDownload = useCallback(async () => {
    const targets = selectedIds.size > 0
      ? sortedPhotos.filter(photo => selectedIds.has(photo.id))
      : sortedPhotos;
    if (targets.length === 0) return;
    let failed = 0;
    for (const photo of targets) {
      try {
        await downloadPhoto(photo);
      } catch {
        failed += 1;
      }
    }
    if (failed > 0) {
      toast.error(`${failed} 张照片下载失败`);
    } else {
      toast.success(`已下载 ${targets.length} 张照片`);
    }
  }, [downloadPhoto, selectedIds, sortedPhotos]);

  const thumbnailUrl = (photo: PhotoResponse) =>
    resolveBackendUrl(photo.thumbnail_url || photo.original_url);

  // ── 前置状态：未登录 / 未选活动 ───────────────────────────────────────────
  if (!isLoggedIn || !eventId) {
    return (
      <div className="flex-1 flex items-center justify-center p-5">
        <GlassCard className="p-8 max-w-md text-center space-y-3">
          <ImageOff size={32} className="mx-auto text-white/30" />
          <div className="text-sm font-semibold text-white">
            {isLoggedIn ? "尚未选择活动" : "尚未登录"}
          </div>
          <p className="text-xs text-white/40 leading-relaxed">
            {isLoggedIn
              ? "相册展示当前活动的真实拍摄照片。请先从活动管理选择一个活动。"
              : "登录并选择活动后，相册会展示该活动的真实拍摄照片。"}
          </p>
          {isLoggedIn && navigate && (
            <GlowBtn size="sm" variant="primary" onClick={() => navigate("events")}>
              <CalendarDays size={14} />前往活动管理
            </GlowBtn>
          )}
        </GlassCard>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto p-5 space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-white">照片相册</h2>
          <p className="text-xs text-white/40 mt-0.5">
            共 {photos.length} 张照片{currentEvent?.name ? ` · ${currentEvent.name}` : ""}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <GlowBtn size="sm" variant="ghost" onClick={() => setLatestFirst(v => !v)}>
            {latestFirst ? <ArrowDownWideNarrow size={14} /> : <ArrowUpNarrowWide size={14} />}
            {latestFirst ? "最新优先" : "最早优先"}
          </GlowBtn>
          <GlowBtn size="sm" variant="ghost" onClick={() => void loadPhotos()}>
            <RefreshCw size={14} className={loading ? "animate-spin" : undefined} />刷新
          </GlowBtn>
          <GlowBtn
            size="sm"
            variant="primary"
            onClick={() => void handleBatchDownload()}
            disabled={photos.length === 0}
          >
            <Download size={14} />
            {selectedIds.size > 0 ? `下载已选 ${selectedIds.size}` : "批量下载"}
          </GlowBtn>
        </div>
      </div>

      {loadError && (
        <GlassCard className="p-4 flex items-center justify-between">
          <span className="text-xs text-red-300">{loadError}</span>
          <GlowBtn size="sm" variant="ghost" onClick={() => void loadPhotos()}>重试</GlowBtn>
        </GlassCard>
      )}

      {loading && photos.length === 0 && (
        <div className="columns-4 gap-3">
          {Array.from({ length: 8 }).map((_, i) => (
            <div key={i} className="break-inside-avoid mb-3 rounded-xl bg-white/5 animate-pulse" style={{ height: 120 + (i % 3) * 40 }} />
          ))}
        </div>
      )}

      {!loading && !loadError && photos.length === 0 && (
        <GlassCard className="p-8 text-center space-y-3">
          <ImageOff size={32} className="mx-auto text-white/30" />
          <div className="text-sm font-semibold text-white">当前活动还没有照片</div>
          <p className="text-xs text-white/40">完成拍摄并上传后，照片会出现在这里。</p>
          {navigate && (
            <GlowBtn size="sm" variant="primary" onClick={() => navigate("camera")}>前往拍摄</GlowBtn>
          )}
        </GlassCard>
      )}

      {sortedPhotos.length > 0 && (
        <div className="columns-4 gap-3">
          {sortedPhotos.map((photo, i) => (
            <motion.div key={photo.id} className="break-inside-avoid mb-3 group cursor-pointer relative rounded-xl overflow-hidden"
              whileHover={{ scale: 1.02, y: -2 }} whileTap={{ scale: 0.98 }} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: Math.min(i * 0.04, 0.4) }}>
              <img src={thumbnailUrl(photo)}
                alt={`活动照片 ${new Date(photo.created_at).toLocaleString()}`}
                className="w-full object-cover" style={{ borderRadius: 12 }} loading="lazy" />
              <div className="absolute inset-0 bg-black/0 group-hover:bg-black/30 transition-all flex items-center justify-center opacity-0 group-hover:opacity-100 rounded-xl">
                <div className="flex gap-2">
                  <GlowBtn size="sm" variant="primary" onClick={(e) => { e.stopPropagation(); setPreviewPhoto(photo); }}><Eye size={13} /></GlowBtn>
                  <GlowBtn size="sm" variant="ghost" onClick={(e) => void handleDownload(photo, e)}>
                    <Download size={13} />
                  </GlowBtn>
                </div>
              </div>
              <div className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity"
                onClick={(e: React.MouseEvent) => { e.stopPropagation(); togglePhoto(photo.id); }}>
                <div className={`w-5 h-5 rounded border-2 backdrop-blur-sm flex items-center justify-center ${
                  selectedIds.has(photo.id)
                    ? "border-violet-500 bg-violet-500/30"
                    : "border-white/80 bg-white/10"
                }`}>
                  {selectedIds.has(photo.id) && (
                    <svg width="10" height="10" viewBox="0 0 10 10" className="text-white"><path d="M2 5l2 2 4-4" stroke="currentColor" strokeWidth="2" fill="none" /></svg>
                  )}
                </div>
              </div>
            </motion.div>
          ))}
        </div>
      )}

      {/* Photo preview modal */}
      <AnimatePresence>
        {previewPhoto && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 bg-black/80 flex items-center justify-center p-8"
            onClick={() => setPreviewPhoto(null)}
          >
            <motion.div
              initial={{ scale: 0.9 }}
              animate={{ scale: 1 }}
              exit={{ scale: 0.9 }}
              className="relative max-w-3xl max-h-full"
              onClick={e => e.stopPropagation()}
            >
              <img src={resolveBackendUrl(previewPhoto.original_url)} alt="相册大图预览" className="max-w-full max-h-[80vh] rounded-2xl object-contain" loading="lazy" />
              <button className="absolute top-3 right-3 w-8 h-8 rounded-full bg-black/50 flex items-center justify-center text-white hover:bg-black/70"
                onClick={() => setPreviewPhoto(null)}>
                <X size={16} />
              </button>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
