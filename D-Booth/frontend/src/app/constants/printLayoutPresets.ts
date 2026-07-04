import type { PhotoElementProps, TemplateLayout } from "../types/template";

export type PrintLayoutFrame = {
  photoNumber: number;
  x: number;
  y: number;
  width: number;
  height: number;
};

export type PrintLayoutPreset = {
  id: string;
  name: string;
  description: string;
  canvasWidth: number;
  canvasHeight: number;
  frames: PrintLayoutFrame[];
};

export const TEMPLATE_EDITOR_QUICK_LAYOUT_SESSION_KEY = "aibooth.templateEditor.quickLayoutId";

export const FEATURED_QUICK_PRINT_LAYOUT_IDS = [
  "one-single-vertical",
  "two-double-horizontal",
  "four-single-horizontal",
  "four-double-vertical",
  "one-large-three-small-horizontal",
] as const;

export const QUICK_PRINT_LAYOUTS: PrintLayoutPreset[] = [
  {
    id: "one-single-vertical",
    name: "1张 单版 竖",
    description: "整张 4x6 竖版",
    canvasWidth: 1200,
    canvasHeight: 1800,
    frames: [{ photoNumber: 1, x: 0, y: 0, width: 1200, height: 1800 }],
  },
  {
    id: "one-single-horizontal",
    name: "1张 单版 横",
    description: "整张 6x4 横版",
    canvasWidth: 1800,
    canvasHeight: 1200,
    frames: [{ photoNumber: 1, x: 0, y: 0, width: 1800, height: 1200 }],
  },
  {
    id: "one-double-vertical",
    name: "1张 双条 竖",
    description: "上下双联",
    canvasWidth: 1200,
    canvasHeight: 1800,
    frames: [
      { photoNumber: 1, x: 0, y: 0, width: 1200, height: 800 },
      { photoNumber: 1, x: 0, y: 1000, width: 1200, height: 800 },
    ],
  },
  {
    id: "one-double-horizontal",
    name: "1张 双条 横",
    description: "左右双联",
    canvasWidth: 1800,
    canvasHeight: 1200,
    frames: [
      { photoNumber: 1, x: 0, y: 0, width: 800, height: 1200 },
      { photoNumber: 1, x: 1000, y: 0, width: 800, height: 1200 },
    ],
  },
  {
    id: "two-double-horizontal",
    name: "2张 双条 横",
    description: "每条 2 张",
    canvasWidth: 1800,
    canvasHeight: 1200,
    frames: [
      { photoNumber: 1, x: 0, y: 0, width: 900, height: 600 },
      { photoNumber: 2, x: 0, y: 600, width: 900, height: 600 },
      { photoNumber: 1, x: 900, y: 0, width: 900, height: 600 },
      { photoNumber: 2, x: 900, y: 600, width: 900, height: 600 },
    ],
  },
  {
    id: "three-double-vertical",
    name: "3张 双条 竖",
    description: "每条 3 张",
    canvasWidth: 1200,
    canvasHeight: 1800,
    frames: [
      { photoNumber: 1, x: 0, y: 0, width: 600, height: 400 },
      { photoNumber: 2, x: 0, y: 400, width: 600, height: 400 },
      { photoNumber: 3, x: 0, y: 800, width: 600, height: 400 },
      { photoNumber: 1, x: 600, y: 0, width: 600, height: 400 },
      { photoNumber: 2, x: 600, y: 400, width: 600, height: 400 },
      { photoNumber: 3, x: 600, y: 800, width: 600, height: 400 },
    ],
  },
  {
    id: "four-single-vertical",
    name: "4张 单版 竖",
    description: "2x2 竖版",
    canvasWidth: 1200,
    canvasHeight: 1800,
    frames: [
      { photoNumber: 1, x: 0, y: 0, width: 600, height: 900 },
      { photoNumber: 2, x: 600, y: 0, width: 600, height: 900 },
      { photoNumber: 3, x: 0, y: 900, width: 600, height: 900 },
      { photoNumber: 4, x: 600, y: 900, width: 600, height: 900 },
    ],
  },
  {
    id: "four-single-horizontal",
    name: "4张 单版 横",
    description: "2x2 横版",
    canvasWidth: 1800,
    canvasHeight: 1200,
    frames: [
      { photoNumber: 1, x: 0, y: 0, width: 900, height: 600 },
      { photoNumber: 2, x: 900, y: 0, width: 900, height: 600 },
      { photoNumber: 3, x: 0, y: 600, width: 900, height: 600 },
      { photoNumber: 4, x: 900, y: 600, width: 900, height: 600 },
    ],
  },
  {
    id: "four-double-vertical",
    name: "4张 双条 竖",
    description: "每条 4 张",
    canvasWidth: 1200,
    canvasHeight: 1800,
    frames: [
      { photoNumber: 1, x: 0, y: 0, width: 600, height: 400 },
      { photoNumber: 2, x: 0, y: 400, width: 600, height: 400 },
      { photoNumber: 3, x: 0, y: 800, width: 600, height: 400 },
      { photoNumber: 4, x: 0, y: 1200, width: 600, height: 400 },
      { photoNumber: 1, x: 600, y: 0, width: 600, height: 400 },
      { photoNumber: 2, x: 600, y: 400, width: 600, height: 400 },
      { photoNumber: 3, x: 600, y: 800, width: 600, height: 400 },
      { photoNumber: 4, x: 600, y: 1200, width: 600, height: 400 },
    ],
  },
  {
    id: "one-large-three-small-horizontal",
    name: "1大3小 横",
    description: "主图加三连拍",
    canvasWidth: 1800,
    canvasHeight: 1200,
    frames: [
      { photoNumber: 1, x: 130, y: 60, width: 1005, height: 670 },
      { photoNumber: 2, x: 40, y: 787, width: 560, height: 373 },
      { photoNumber: 3, x: 620, y: 787, width: 560, height: 373 },
      { photoNumber: 4, x: 1200, y: 787, width: 560, height: 373 },
    ],
  },
];

export function createTemplateLayoutFromPrintPreset(layoutId: string, preset: PrintLayoutPreset): TemplateLayout {
  return {
    id: layoutId,
    name: preset.name,
    paperSize: {
      width: Number((preset.canvasWidth * 25.4 / 300).toFixed(1)),
      height: Number((preset.canvasHeight * 25.4 / 300).toFixed(1)),
    },
    resolution: 300,
    orientation: preset.canvasWidth > preset.canvasHeight ? "landscape" : "portrait",
    background: { type: "color", value: "#ffffff" },
    elements: preset.frames.map((frame, index) => ({
      id: `${layoutId}_photo_${index + 1}`,
      type: "photo",
      x: frame.x,
      y: frame.y,
      width: frame.width,
      height: frame.height,
      rotation: 0,
      opacity: 1,
      zIndex: index,
      locked: false,
      visible: true,
      props: {
        photoNumber: frame.photoNumber,
        cropMode: "stretch",
        borderRadius: 0,
      } as PhotoElementProps,
    })),
  };
}
