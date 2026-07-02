import { useState, useCallback } from "react";
import { Filter, Download, Share2, Eye, X } from "lucide-react";
import { motion, AnimatePresence } from "motion/react";
import { GlassCard } from "../components/GlassCard";
import { GlowBtn } from "../components/GlowBtn";
import { showToast } from "../stores/useToast";
import type { Screen } from "../types";

interface GalleryScreenProps {
  navigate?: (s: Screen) => void;
}

export function GalleryScreen({ navigate }: GalleryScreenProps) {
  const photos = [
    { src: '/images/scenes/wedding-couple-booth.webp', alt: '婚礼新人' },
    { src: '/images/scenes/wedding-guests-fun.webp', alt: '婚礼宾客' },
    { src: '/images/scenes/corporate-event-group.webp', alt: '企业活动' },
    { src: '/images/scenes/conference-networking.webp', alt: '会议交流' },
    { src: '/images/scenes/birthday-party-fun.webp', alt: '生日派对' },
    { src: '/images/scenes/kids-birthday-booth.webp', alt: '儿童生日' },
    { src: '/images/scenes/brand-popup-mall.webp', alt: '品牌快闪' },
    { src: '/images/scenes/festival-outdoor-booth.webp', alt: '音乐节' },
    { src: '/images/products/ipad-booth-setup.webp', alt: 'iPad照相亭' },
    { src: '/images/products/camera-equipment.webp', alt: '相机设备' },
    { src: '/images/products/printer-dnp-ds620.webp', alt: '打印机' },
    { src: '/images/products/photo-prints-showcase.webp', alt: '照片成品' },
  ];

  const [showFilters, setShowFilters] = useState(false);
  const [selectedPhoto, setSelectedPhoto] = useState<string | null>(null);
  const [selectedPhotos, setSelectedPhotos] = useState<Set<string>>(new Set());
  const [downloading, setDownloading] = useState<string | null>(null);

  const togglePhoto = (src: string) => {
    setSelectedPhotos(prev => {
      const next = new Set(prev);
      if (next.has(src)) next.delete(src);
      else next.add(src);
      return next;
    });
  };

  const handleDownload = useCallback((alt: string, src: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setDownloading(src);
    const id = showToast.loading("正在下载...");
    setTimeout(() => {
      showToast.success("下载完成");
      setDownloading(null);
    }, 1000);
  }, []);

  return (
    <div className="flex-1 overflow-y-auto p-5 space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-white">照片相册</h2>
          <p className="text-xs text-white/40 mt-0.5">共 {photos.length} 张照片 · 夏日派对 2026</p>
        </div>
        <div className="flex items-center gap-2">
          <GlowBtn size="sm" variant="ghost" onClick={() => showToast.info("批量下载功能开发中")}><Download size={14} />批量下载</GlowBtn>
          <GlowBtn size="sm" variant="primary" onClick={() => showToast.info("分享相册功能开发中")}><Share2 size={14} />分享相册</GlowBtn>
        </div>
      </div>

      {/* Filter panel */}
      {showFilters && (
        <GlassCard className="p-4">
          <div className="flex items-center gap-4">
            <span className="text-xs text-white/40">按分类筛选：</span>
            {["全部", "场景", "产品", "人物"].map(f => (
              <button key={f} className="px-3 py-1 rounded-lg text-xs bg-white/5 text-white/60 hover:bg-white/10 hover:text-white transition-colors">
                {f}
              </button>
            ))}
          </div>
        </GlassCard>
      )}

      <div className="columns-4 gap-3">
        {photos.map((photo, i) => (
          <motion.div key={photo.src} className="break-inside-avoid mb-3 group cursor-pointer relative rounded-xl overflow-hidden"
            whileHover={{ scale: 1.02, y: -2 }} whileTap={{ scale: 0.98 }} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.05 }}>
            <img src={photo.src}
              alt={photo.alt} className="w-full object-cover" style={{ borderRadius: 12 }} loading="lazy" />
            <div className="absolute inset-0 bg-black/0 group-hover:bg-black/30 transition-all flex items-center justify-center opacity-0 group-hover:opacity-100 rounded-xl">
              <div className="flex gap-2">
                <GlowBtn size="sm" variant="primary" onClick={(e) => { e.stopPropagation(); setSelectedPhoto(photo.src); }}><Eye size={13} /></GlowBtn>
                <GlowBtn size="sm" variant="ghost" className={downloading === photo.src ? "opacity-50 pointer-events-none" : ""} onClick={(e) => handleDownload(photo.alt, photo.src, e)}>
                  <Download size={13} />
                </GlowBtn>
              </div>
            </div>
            <div className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity"
              onClick={(e: React.MouseEvent) => { e.stopPropagation(); togglePhoto(photo.src); }}>
              <div className={`w-5 h-5 rounded border-2 backdrop-blur-sm flex items-center justify-center ${
                selectedPhotos.has(photo.src)
                  ? "border-violet-500 bg-violet-500/30"
                  : "border-white/80 bg-white/10"
              }`}>
                {selectedPhotos.has(photo.src) && (
                  <svg width="10" height="10" viewBox="0 0 10 10" className="text-white"><path d="M2 5l2 2 4-4" stroke="currentColor" strokeWidth="2" fill="none" /></svg>
                )}
              </div>
            </div>
          </motion.div>
        ))}
      </div>

      {/* Photo preview modal */}
      <AnimatePresence>
        {selectedPhoto && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 bg-black/80 flex items-center justify-center p-8"
            onClick={() => setSelectedPhoto(null)}
          >
            <motion.div
              initial={{ scale: 0.9 }}
              animate={{ scale: 1 }}
              exit={{ scale: 0.9 }}
              className="relative max-w-3xl max-h-full"
              onClick={e => e.stopPropagation()}
            >
              <img src={selectedPhoto} alt="相册大图预览" className="max-w-full max-h-[80vh] rounded-2xl object-contain" loading="lazy" />
              <button className="absolute top-3 right-3 w-8 h-8 rounded-full bg-black/50 flex items-center justify-center text-white hover:bg-black/70"
                onClick={() => setSelectedPhoto(null)}>
                <X size={16} />
              </button>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
