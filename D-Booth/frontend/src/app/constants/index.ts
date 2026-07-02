/**
 * Centralized application constants.
 *
 * All screen-level inline data (mock charts, printer lists, filter sets,
 * fallback images, QR patterns, preset images, etc.) are collected here
 * to keep components lean and enable single-source-of-truth updates.
 */

// ─── Camera Screen ───────────────────────────────────────────────────────────

export const CAMERA_FILTERS = ["自然", "清新", "复古", "胶片", "韩系", "日系", "奶油", "糖果"] as const;

export const RECENT_PHOTOS = [
  "/images/scenes/wedding-couple-booth.webp",
  "/images/scenes/birthday-party-fun.webp",
  "/images/scenes/corporate-event-group.webp",
  "/images/products/photo-prints-showcase.webp",
  "/images/scenes/festival-outdoor-booth.webp",
  "/images/products/polaroid-style-prints.webp",
] as const;

export const FORMAT_OPTIONS = ["4:3", "16:9", "1:1"] as const;

// ─── Beauty Screen ───────────────────────────────────────────────────────────

export const BEAUTY_PRESETS = ["原图", "自然", "清新", "白皙", "元气", "高级", "胶片", "奶油", "韩系", "日系"] as const;

export const DEFAULT_BEAUTY_VALUES = {
  smooth: 60,
  thinFace: 40,
  bigEye: 35,
  eyeLight: 50,
  whiten: 45,
  acne: 30,
  nasolabial: 40,
  teethWhiten: 50,
  lipColor: 20,
} as const;

export const BEAUTY_FALLBACK_IMAGE = "/images/avatars/avatar-woman-asian-01.webp";

export const BEAUTY_PRESET_AVATARS = [
  "/images/avatars/avatar-woman-asian-01.webp",
  "/images/avatars/avatar-woman-latina-01.webp",
  "/images/avatars/avatar-woman-african-01.webp",
  "/images/avatars/avatar-teen-girl.webp",
  "/images/avatars/avatar-man-asian-01.webp",
  "/images/avatars/avatar-man-caucasian-01.webp",
  "/images/avatars/avatar-man-african-01.webp",
  "/images/avatars/avatar-elderly-couple.webp",
  "/images/avatars/avatar-woman-asian-01.webp",
  "/images/avatars/avatar-woman-latina-01.webp",
] as const;

// ─── Print Screen ────────────────────────────────────────────────────────────

export const MAX_PRINT_QTY = 10;

export const PRINTERS = [
  { name: "DNP DS620", status: "就绪", color: "green" as const },
  { name: "Mitsubishi CP-D70", status: "忙碌", color: "yellow" as const },
  { name: "Canon SELPHY", status: "离线", color: "red" as const },
] as const;

export const PAPER_SIZES = ["2×6 英寸", "4×6 英寸", "5×7 英寸", "A6 尺寸"] as const;

export const COLOR_MODES = ["自动", "鲜艳", "自然", "柔和"] as const;

export const PRINT_PREVIEW_FALLBACKS = [
  "/images/scenes/wedding-couple-booth.webp",
  "/images/scenes/birthday-party-fun.webp",
  "/images/products/photo-prints-showcase.webp",
] as const;

export const PRINT_HISTORY = [
  { name: "DNP DS620", count: 89, status: "正常", ink: 68 },
  { name: "DNP DS620", count: 67, status: "正常", ink: 45 },
  { name: "Mitsubishi CP-D70", count: 0, status: "忙碌", ink: 92 },
] as const;

// ─── Sharing Screen ──────────────────────────────────────────────────────────

export const SHARING_FALLBACK_IMAGE = "/images/scenes/wedding-couple-booth.webp";

export const QR_PATTERN = [
  1, 1, 1, 0, 1, 1, 1, 1, 0, 1, 1, 1, 0, 1, 1, 1, 1, 0, 1, 1, 1, 0, 1, 0, 1,
  0, 1, 0, 1, 1, 1, 0, 1, 1, 1, 1, 0, 1, 0, 1, 0, 1, 1, 1, 1, 0, 1, 1, 1, 0,
  1, 0, 1, 0, 1, 1, 1, 1, 1, 0, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 1, 1, 1, 0, 1,
  1, 1, 0, 1, 0, 1, 1, 0, 1, 1, 0, 1, 0, 1, 1, 0, 0, 1, 1, 0, 1, 0, 1, 1, 1,
  1, 0, 1, 1, 1,
];

export const SHARE_METHODS = [
  { icon: "QrCode", label: "二维码下载", color: "from-violet-600 to-violet-800", channel: "qr" },
  { icon: "Bluetooth", label: "AirDrop", color: "from-blue-600 to-blue-800", channel: "airdrop" },
  { icon: "Globe", label: "微信分享", color: "from-emerald-600 to-emerald-800", channel: "wechat" },
  { icon: "Mail", label: "邮件发送", color: "from-orange-600 to-orange-800", channel: "email" },
  { icon: "Cloud", label: "云端相册", color: "from-pink-600 to-pink-800", channel: "cloud" },
] as const;

export const SHARE_STATS = [
  { label: "二维码扫描", value: "128", trend: "+12%" },
  { label: "照片下载", value: "56", trend: "+8%" },
  { label: "分享次数", value: "42", trend: "+15%" },
] as const;

// ─── Analytics Screen ────────────────────────────────────────────────────────

export const ANALYTICS_SUMMARY_CARDS = [
  { label: "总拍摄量", value: "12,856", trend: "+23.5%" },
  { label: "总打印量", value: "8,234", trend: "+18.2%" },
  { label: "活跃活动", value: "24", trend: "+4" },
  { label: "月度收入", value: "¥41,300", trend: "+31.8%" },
] as const;

export const WEEK_DATA = [
  { day: "周一", photos: 230, prints: 180, revenue: 2300 },
  { day: "周二", photos: 345, prints: 290, revenue: 3450 },
  { day: "周三", photos: 280, prints: 220, revenue: 2800 },
  { day: "周四", photos: 410, prints: 360, revenue: 4100 },
  { day: "周五", photos: 520, prints: 440, revenue: 5200 },
  { day: "周六", photos: 680, prints: 580, revenue: 6800 },
  { day: "周日", photos: 490, prints: 410, revenue: 4900 },
] as const;

export const PIE_DATA = [
  { name: "婚礼", value: 35 },
  { name: "企业", value: 28 },
  { name: "生日", value: 20 },
  { name: "其他", value: 17 },
] as const;

export const PIE_COLORS = ["#8b5cf6", "#ec4899", "#3b82f6", "#22c55e"] as const;

export const TIME_RANGES = ["今日", "本周", "本月", "全年"] as const;

// ─── Events Screen ───────────────────────────────────────────────────────────

export const DEMO_EVENTS = [
  { id: "demo-event-1", name: "夏日派对 2026", date: "2026-06-10", status: "进行中", photos: 1234, prints: 856, guests: 234, qr: 1892, revenue: "¥12,800" },
  { id: "demo-event-2", name: "婚礼庆典 2026", date: "2026-06-08", status: "已完成", photos: 2341, prints: 1890, guests: 412, qr: 3241, revenue: "¥28,500" },
  { id: "demo-event-3", name: "毕业典礼 2026", date: "2026-06-15", status: "即将开始", photos: 0, prints: 0, guests: 0, qr: 0, revenue: "¥0" },
] as const;

export const EVENT_STATUS_LABEL: Record<string, string> = {
  active: "进行中",
  completed: "已完成",
  scheduled: "即将开始",
  draft: "草稿",
  cancelled: "已取消",
};

export const EVENT_SUMMARY_CARDS = [
  { label: "总活动数", value: "24" },
  { label: "本月收入", value: "¥41,300" },
  { label: "总拍摄量", value: "12,856" },
  { label: "总打印量", value: "8,234" },
] as const;

export const RECENT_ACTIVITIES = [
  { action: "拍摄完成", detail: "夏日派对 · 共 12 张", time: "2 分钟前", color: "violet" as const },
  { action: "打印任务", detail: "完成 5 张打印", time: "8 分钟前", color: "blue" as const },
  { action: "新访客", detail: "3 人扫码下载", time: "15 分钟前", color: "green" as const },
  { action: "云同步", detail: "已同步 24 张照片", time: "20 分钟前", color: "pink" as const },
] as const;

export const EVENT_STATUS_COLORS: Record<string, string> = {
  "进行中": "text-emerald-400 bg-emerald-400/10 border-emerald-400/20",
  "已完成": "text-blue-400 bg-blue-400/10 border-blue-400/20",
  "即将开始": "text-yellow-400 bg-yellow-400/10 border-yellow-400/20",
};

// ─── Sticker/Props System ────────────────────────────────────────────────────

export const DEFAULT_PROPS = [
  // 表情分类
  { id: "prop-1", name: "樱花", category: "表情", imageUrl: "🌸" },
  { id: "prop-2", name: "闪亮", category: "表情", imageUrl: "✨" },
  { id: "prop-3", name: "爱心", category: "表情", imageUrl: "💕" },
  { id: "prop-4", name: "星星", category: "表情", imageUrl: "🌟" },

  // 装饰分类
  { id: "prop-5", name: "蝴蝶结", category: "装饰", imageUrl: "🎀" },
  { id: "prop-6", name: "蝴蝶", category: "装饰", imageUrl: "🦋" },
  { id: "prop-7", name: "皇冠", category: "装饰", imageUrl: "👑" },
  { id: "prop-8", name: "礼帽", category: "装饰", imageUrl: "🎩" },

  // 节日分类
  { id: "prop-9", name: "牛仔帽", category: "节日", imageUrl: "🤠" },
  { id: "prop-10", name: "面具", category: "节日", imageUrl: "🎭" },
  { id: "prop-11", name: "戒指", category: "节日", imageUrl: "💍" },
  { id: "prop-12", name: "庆祝", category: "节日", imageUrl: "🎉" },
] as const;