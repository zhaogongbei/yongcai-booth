import { useState, useEffect } from "react";
import { Camera, Users, Printer, Download, ChevronDown, Music, SkipBack, Pause, Play, SkipForward, Volume2, VolumeX, CloudSun } from "lucide-react";
import { motion, AnimatePresence } from "motion/react";
import { GlassCard } from "../components/GlassCard";
import { GLASS_SELECT_OPTION_CLASS_NAME, getGlassSelectClassName } from "../components/glassSelect";
import { Screen } from "../types";
import { useSettings } from "../stores/useSettings";
import { attendantPlayer } from "../services/attendantPlayer";

// Deterministic QR pattern (5x5, ~60% fill rate — mimics a real QR corner)
const QR_PATTERN = [
  1,1,1,1,1,
  1,0,0,0,1,
  1,0,1,0,1,
  1,0,0,0,1,
  1,1,1,1,1,
];

// Playlist for the music player
const PLAYLIST = [
  { title: "Happy Together", artist: "The Turtles" },
  { title: "Here Comes the Sun", artist: "The Beatles" },
  { title: "Don't Stop Me Now", artist: "Queen" },
  { title: "Walking on Sunshine", artist: "Katrina & The Waves" },
];

const TEMPLATE_LIST = [
  '/images/backgrounds/attract-screen-01.webp',
  '/images/backgrounds/attract-screen-elegant.webp',
  '/images/backgrounds/attract-screen-corporate.webp',
];

const THEME_COLORS = ["#8b5cf6", "#ec4899", "#3b82f6", "#22c55e", "#f59e0b"];

const INTERVAL_OPTIONS = [
  { value: "5", label: "5 秒" },
  { value: "10", label: "10 秒" },
];

const TRANSITION_OPTIONS = [
  { value: "fade", label: "淡入淡出" },
  { value: "slide", label: "滑动" },
];

function hexToRgba(hex: string, alpha: number) {
  const h = hex.replace("#", "");
  const r = parseInt(h.slice(0, 2), 16);
  const g = parseInt(h.slice(2, 4), 16);
  const b = parseInt(h.slice(4, 6), 16);
  return `rgba(${r},${g},${b},${alpha})`;
}

export function AttractScreen({ navigate }: { navigate: (screen: Screen) => void }) {
  const [playing, setPlaying] = useState(true);
  const [muted, setMuted] = useState(false);
  const [trackIndex, setTrackIndex] = useState(0);

  // 循环播放吸引屏语音
  useEffect(() => {
    let timer: NodeJS.Timeout;

    const playAttractVoice = async () => {
      await attendantPlayer.playForTiming("attract_screen");
      // 每30秒播放一次
      timer = setTimeout(playAttractVoice, 30000);
    };

    playAttractVoice();

    return () => {
      clearTimeout(timer);
      attendantPlayer.stop();
    };
  }, []);

  const { settings, updateSettings } = useSettings();
  const a = settings.attract;
  const setA = (patch: Partial<typeof a>) => updateSettings({ attract: { ...a, ...patch } });

  const autoPlay = a.autoPlay;
  const selectedTemplate = a.selectedTemplate ?? 0;
  const selectedColor = a.selectedColor ?? 0;
  const carouselInterval = a.carouselInterval;
  const transition = a.transition;

  const activeTemplate = ((selectedTemplate % TEMPLATE_LIST.length) + TEMPLATE_LIST.length) % TEMPLATE_LIST.length;
  const themePrimary = THEME_COLORS[((selectedColor % THEME_COLORS.length) + THEME_COLORS.length) % THEME_COLORS.length];
  const themeAccent = THEME_COLORS[((selectedColor + 1) % THEME_COLORS.length + THEME_COLORS.length) % THEME_COLORS.length];
  const backgroundSrc = TEMPLATE_LIST[activeTemplate];

  // 自动轮播模板
  useEffect(() => {
    if (!autoPlay) return;
    const ms = parseInt(carouselInterval, 10) * 1000;
    const timer = setInterval(() => {
      setA({ selectedTemplate: (activeTemplate + 1) % TEMPLATE_LIST.length });
    }, ms);
    return () => clearInterval(timer);
  }, [autoPlay, carouselInterval, activeTemplate]);

  const currentTrack = PLAYLIST[trackIndex];

  const handlePrev = () => setTrackIndex(i => (i - 1 + PLAYLIST.length) % PLAYLIST.length);
  const handleNext = () => setTrackIndex(i => (i + 1) % PLAYLIST.length);

  const galleryPhotos = [
    '/images/scenes/wedding-couple-booth.webp',
    '/images/scenes/wedding-guests-fun.webp',
    '/images/scenes/birthday-party-fun.webp',
    '/images/scenes/corporate-event-group.webp',
    '/images/scenes/festival-outdoor-booth.webp',
    '/images/products/photo-prints-showcase.webp',
    '/images/products/polaroid-style-prints.webp',
    '/images/scenes/brand-popup-mall.webp',
  ];

  return (
    <div className="flex-1 flex overflow-hidden">
      {/* Main display */}
      <div className="flex-1 relative overflow-hidden">
        {/* Background */}
        <div className="absolute inset-0">
          <AnimatePresence mode="wait">
            <motion.img
              key={activeTemplate}
              src={backgroundSrc}
              alt="活动背景"
              className="absolute inset-0 w-full h-full object-cover"
              initial={transition === "slide" ? { opacity: 0, x: 40 } : { opacity: 0 }}
              animate={transition === "slide" ? { opacity: 0.55, x: 0 } : { opacity: 0.55 }}
              exit={transition === "slide" ? { opacity: 0, x: -40 } : { opacity: 0 }}
              transition={{ duration: 0.6, ease: "easeInOut" }}
              loading="lazy"
            />
          </AnimatePresence>
          <div
            className="absolute inset-0"
            style={{
              background: `linear-gradient(135deg, ${hexToRgba(themePrimary, 0.6)} 0%, rgba(5,8,22,0.8) 50%, ${hexToRgba(themeAccent, 0.4)} 100%)`,
            }}
          />
          <div className="absolute inset-0" style={{ background: "radial-gradient(ellipse at center, transparent 20%, rgba(5,8,22,0.6) 80%)" }} />
        </div>

        {/* Neon light effects */}
        {[...Array(4)].map((_, i) => (
          <motion.div key={i}
            className="absolute rounded-full"
            style={{
              width: 300 + i * 100,
              height: 300 + i * 100,
              left: `${10 + i * 20}%`,
              top: `${10 + i * 15}%`,
              background: i % 2 === 0 ? hexToRgba(themePrimary, 0.08) : hexToRgba(themeAccent, 0.06),
              filter: "blur(40px)",
            }}
            animate={{ scale: [1, 1.2, 1], opacity: [0.5, 0.8, 0.5] }}
            transition={{ duration: 4 + i, repeat: Infinity, ease: "easeInOut" }}
          />
        ))}

        {/* Main content */}
        <div className="relative z-10 h-full flex flex-col items-center justify-center">
          <motion.div
            className="text-center mb-8"
            initial={{ y: 20, opacity: 0 }} animate={{ y: 0, opacity: 1 }} transition={{ duration: 0.8 }}
          >
            <div className="text-white/60 text-base font-light tracking-[0.3em] uppercase mb-4">
              Welcome To
            </div>
            <h1 className="text-7xl font-black mb-2 tracking-tight"
              style={{
                background: "linear-gradient(135deg, #fff 0%, #c4b5fd 40%, #ec4899 80%, #fff 100%)",
                WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent",
                textShadow: "none",
                filter: "drop-shadow(0 0 30px rgba(139,92,246,0.5))",
              }}>
              SUMMER PARTY
            </h1>
            <h2 className="text-7xl font-black tracking-tight"
              style={{
                background: "linear-gradient(135deg, #ec4899 0%, #8b5cf6 50%, #3b82f6 100%)",
                WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent",
                filter: "drop-shadow(0 0 30px rgba(236,72,153,0.5))",
              }}>
              2026
            </h2>
            <div className="flex items-center justify-center gap-2 mt-3 text-white/40 text-sm tracking-widest">
              <span className="w-12 h-px bg-white/20" />
              ✦ AI EVENT EXPERIENCE ✦
              <span className="w-12 h-px bg-white/20" />
            </div>
          </motion.div>

          <motion.button
            type="button"
            onClick={() => navigate("camera")}
            className="relative mb-8 px-14 py-5 rounded-full border-2 border-white/80 text-white text-xl font-bold tracking-widest cursor-pointer appearance-none outline-none"
            style={{ background: "rgba(255,255,255,0.08)", backdropFilter: "blur(20px)" }}
            whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}
            animate={{ boxShadow: [`0 0 40px ${hexToRgba(themePrimary, 0.4)}`, `0 0 80px ${hexToRgba(themePrimary, 0.8)}`, `0 0 40px ${hexToRgba(themePrimary, 0.4)}`] }}
            transition={{ duration: 2, repeat: Infinity }}
          >
            TOUCH TO START
            <div className="absolute -bottom-6 left-1/2 -translate-x-1/2 pointer-events-none">
              <motion.div animate={{ y: [0, 4, 0] }} transition={{ duration: 1.5, repeat: Infinity }}>
                <ChevronDown size={20} className="text-white/40" />
              </motion.div>
            </div>
          </motion.button>

          {/* Stats */}
          <div className="flex items-center gap-8 mt-6">
            {[
              { icon: Camera, label: "Photos Captured", value: "12,856" },
              { icon: Users, label: "Guests Participated", value: "1,234" },
              { icon: Printer, label: "Photos Printed", value: "5,284" },
              { icon: Download, label: "QR Downloads", value: "3,672" },
            ].map(s => (
              <div key={s.label} className="flex items-center gap-2 text-center">
                <div className="w-8 h-8 rounded-lg bg-white/10 flex items-center justify-center">
                  <s.icon size={16} className="text-white/60" />
                </div>
                <div className="text-left">
                  <div className="text-lg font-bold text-white">{s.value}</div>
                  <div className="text-[10px] text-white/40">{s.label}</div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Gallery strip */}
        <div className="absolute bottom-0 left-0 right-0">
          <div className="flex items-center justify-between px-4 py-2">
            <span className="text-xs text-white/40">精彩瞬间</span>
            <div className="flex items-center gap-2">
              <span className="text-xs text-white/30">自动播放</span>
              <div
                className={`w-8 h-4 rounded-full relative cursor-pointer ${autoPlay ? "bg-violet-500" : "bg-white/20"}`}
                onClick={() => setA({ autoPlay: !autoPlay })}
              >
                <div className={`absolute top-0.5 w-3 h-3 rounded-full bg-white transition-all ${autoPlay ? "right-0.5" : "left-0.5"}`} />
              </div>
            </div>
          </div>
          <div className="flex gap-2 px-4 pb-4 overflow-hidden">
            {galleryPhotos.map((src, i) => (
              <motion.div key={i} className="flex-shrink-0 w-24 h-16 rounded-xl overflow-hidden border border-white/10"
                initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: i * 0.1 }}>
                <img src={src}
                  alt={`活动相册图 ${i + 1}`} className="w-full h-full object-cover" loading="lazy" />
              </motion.div>
            ))}
          </div>
        </div>

        {/* Music player */}
        <div className="absolute bottom-32 left-4">
          <GlassCard className="px-4 py-3 flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-violet-500 to-pink-500 flex items-center justify-center">
              <Music size={14} className="text-white" />
            </div>
            <div>
              <div className="text-xs text-white">{currentTrack.title}</div>
              <div className="text-[10px] text-white/40">{currentTrack.artist}</div>
            </div>
            <div className="flex items-center gap-1 ml-2">
              <button className="p-1 text-white/40 hover:text-white" onClick={handlePrev}><SkipBack size={14} /></button>
              <button onClick={() => setPlaying(!playing)} className="p-1 text-white/70 hover:text-white">
                {playing ? <Pause size={14} /> : <Play size={14} />}
              </button>
              <button className="p-1 text-white/40 hover:text-white" onClick={handleNext}><SkipForward size={14} /></button>
              <button onClick={() => setMuted(!muted)} className="p-1 text-white/40 hover:text-white">
                {muted ? <VolumeX size={14} /> : <Volume2 size={14} />}
              </button>
            </div>
          </GlassCard>
        </div>

        {/* Weather + time */}
        <div className="absolute bottom-32 right-[290px] flex gap-2">
          <GlassCard className="px-3 py-2 flex items-center gap-2">
            <CloudSun size={16} className="text-yellow-400" />
            <div>
              <div className="text-xs text-white">28°C</div>
              <div className="text-[10px] text-white/40">多云</div>
            </div>
          </GlassCard>
          <GlassCard className="px-3 py-2">
            <div className="text-lg font-mono font-bold text-white">19:41</div>
            <div className="text-[10px] text-white/40">2026年6月10日 星期三</div>
          </GlassCard>
        </div>
      </div>

      {/* Right control panel */}
      <GlassCard className="w-72 rounded-none border-l border-white/5 overflow-y-auto p-4 space-y-4">
        <div className="text-xs font-semibold text-white/60 uppercase tracking-wider">待机页设置</div>

        {/* Template */}
        <div>
          <div className="text-xs text-white/40 mb-2">模板选择</div>
          <div className="grid grid-cols-3 gap-1.5 mb-2">
            {TEMPLATE_LIST.map((src, i) => (
              <button
                key={src}
                type="button"
                className={`aspect-video rounded-lg overflow-hidden border-2 cursor-pointer p-0 appearance-none bg-transparent outline-none transition-colors ${i === activeTemplate ? "border-violet-500" : "border-transparent hover:border-white/30"}`}
                onClick={() => setA({ selectedTemplate: i })}
              >
                <img src={src} alt={`欢迎屏模板 ${i + 1}`} className="w-full h-full object-cover pointer-events-none" loading="lazy" />
              </button>
            ))}
          </div>
          <button className="text-xs text-violet-400 hover:text-violet-300" onClick={() => navigate("gallery")}>查看更多 →</button>
        </div>

        {/* Theme color */}
        <div>
          <div className="text-xs text-white/40 mb-2">主题风格</div>
          <div className="flex gap-2">
            {THEME_COLORS.map((c, i) => (
              <div key={c}
                className={`w-8 h-8 rounded-full cursor-pointer border-2 transition-transform hover:scale-110 ${i === selectedColor ? "border-white" : "border-transparent"}`}
                style={{ background: c }}
                onClick={() => setA({ selectedColor: i })}
              />
            ))}
          </div>
        </div>

        {/* Auto play settings */}
        <div className="space-y-2">
          <div className="text-xs text-white/40">自动轮播</div>
          <div className="flex items-center justify-between">
            <span className="text-xs text-white/60">轮播间隔</span>
            <select
              className={getGlassSelectClassName("rounded-lg px-2 py-1 text-xs")}
              value={carouselInterval}
              onChange={e => setA({ carouselInterval: e.target.value })}
            >
              {INTERVAL_OPTIONS.map(option => <option key={option.value} value={option.value} className={GLASS_SELECT_OPTION_CLASS_NAME}>{option.label}</option>)}
            </select>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-xs text-white/60">过渡效果</span>
            <select
              className={getGlassSelectClassName("rounded-lg px-2 py-1 text-xs")}
              value={transition}
              onChange={e => setA({ transition: e.target.value })}
            >
              {TRANSITION_OPTIONS.map(option => <option key={option.value} value={option.value} className={GLASS_SELECT_OPTION_CLASS_NAME}>{option.label}</option>)}
            </select>
          </div>
        </div>

        {/* Welcome text */}
        <div>
          <div className="text-xs text-white/40 mb-2">欢迎语设置</div>
          <div className="bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-xs text-white/50">
            Welcome To SUMMER PARTY 2026
          </div>
        </div>

        {/* QR code */}
        <div className="border-t border-white/5 pt-4">
          <div className="text-xs text-white/40 mb-2">品牌定制 <span className="text-violet-400">已启用</span></div>
          <GlassCard className="p-3 flex items-center gap-3">
            <div className="w-14 h-14 bg-white rounded-xl p-1.5">
              <div className="w-full h-full bg-gray-900 rounded grid grid-cols-5 gap-0.5 p-1">
                {QR_PATTERN.map((v, i) => (
                  <div key={i} className={`rounded-[1px] ${v ? "bg-white" : "bg-transparent"}`} />
                ))}
              </div>
            </div>
            <div>
              <div className="text-xs text-white font-medium">扫描二维码</div>
              <div className="text-[10px] text-white/40">分享照片</div>
            </div>
          </GlassCard>
        </div>

        {/* Recent events */}
        <div className="border-t border-white/5 pt-4">
          <div className="text-xs text-white/40 mb-2 flex items-center justify-between">
            <span>即将到来的活动</span>
            <button className="text-violet-400 hover:text-violet-300">查看全部</button>
          </div>
          {[
            { name: "企业庆典 2026", date: "6月15日 18:00" },
            { name: "婚礼庆典 2026", date: "6月18日 14:00" },
            { name: "毕业典礼 2026", date: "6月20日 09:00" },
          ].map(e => (
            <div key={e.name} className="flex items-center gap-2 py-2 border-b border-white/3">
              <div className="w-1.5 h-1.5 rounded-full bg-violet-400" />
              <div className="flex-1">
                <div className="text-xs text-white">{e.name}</div>
                <div className="text-[10px] text-white/40">{e.date}</div>
              </div>
            </div>
          ))}
        </div>
      </GlassCard>
    </div>
  );
}
