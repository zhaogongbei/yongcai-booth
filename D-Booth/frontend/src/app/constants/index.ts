/**
 * Centralized application constants.
 *
 * Shared screen-level constants (filter sets, fallback images,
 * QR patterns, preset images, etc.) are collected here
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

// ─── Sharing Screen ──────────────────────────────────────────────────────────

export const SHARING_FALLBACK_IMAGE = "/images/scenes/wedding-couple-booth.webp";

export const QR_PATTERN = [
  1, 1, 1, 0, 1, 1, 1, 1, 0, 1, 1, 1, 0, 1, 1, 1, 1, 0, 1, 1, 1, 0, 1, 0, 1,
  0, 1, 0, 1, 1, 1, 0, 1, 1, 1, 1, 0, 1, 0, 1, 0, 1, 1, 1, 1, 0, 1, 1, 1, 0,
  1, 0, 1, 0, 1, 1, 1, 1, 1, 0, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 1, 1, 1, 0, 1,
  1, 1, 0, 1, 0, 1, 1, 0, 1, 1, 0, 1, 0, 1, 1, 0, 0, 1, 1, 0, 1, 0, 1, 1, 1,
  1, 0, 1, 1, 1,
];

export const EVENT_STATUS_LABEL: Record<string, string> = {
  active: "进行中",
  completed: "已完成",
  scheduled: "即将开始",
  draft: "草稿",
  cancelled: "已取消",
};

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
