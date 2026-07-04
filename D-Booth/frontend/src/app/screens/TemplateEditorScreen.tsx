import { useState, useCallback, useEffect, useRef, type WheelEvent as ReactWheelEvent } from "react";
import { ArrowLeft, ChevronDown, Eye, Download, Move, Copy, Layers, AlignCenter, Type, Palette, Lock, Trash2, Undo2, Redo2, Plus, LayoutTemplate, ChevronUp, GripVertical, Image as ImageIcon, ScanQrCode, Square, Type as TypeIcon, Calendar, Save, Upload } from "lucide-react";
import { motion, AnimatePresence } from "motion/react";
import { GlassCard } from "../components/GlassCard";
import { GlowBtn } from "../components/GlowBtn";
import { TopBar } from "../components/TopBar";
import { showToast } from "../stores/useToast";
import { useSettings } from "../stores/useSettings";
import { useCaptureFlow } from "../stores/useCaptureFlow";
import { useUndoRedo } from "../hooks/useUndoRedo";
import { TEMPLATE_PRESETS } from "../constants/templatePresets";
import { createTemplateLayoutFromPrintPreset, QUICK_PRINT_LAYOUTS, TEMPLATE_EDITOR_QUICK_LAYOUT_SESSION_KEY, type PrintLayoutPreset } from "../constants/printLayoutPresets";
import type { TemplateElement, ElementProps, TemplateLayout, PhotoElementProps, TextElementProps, ShapeElementProps, DateElementProps, QrCodeElementProps, ImageElementProps } from "../types/template";
import { createTemplate, getMyTeams, getTemplate, updateTemplate, validateTemplate } from "../../lib/api";
import type { Screen } from "../types";

const ZOOM_OPTIONS = [
  { label: "25%", value: 0.25 },
  { label: "50%", value: 0.5 },
  { label: "75%", value: 0.75 },
  { label: "100%", value: 1 },
  { label: "150%", value: 1.5 },
  { label: "200%", value: 2 },
];

const MINIMUM_ELEMENT_SIZE = 60;
const SNAP_THRESHOLD = 18;
const BACKGROUND_LAYER_ID = '__template_background_layer__';

type SnapGuide = {
  orientation: 'vertical' | 'horizontal';
  position: number;
};

type SnapCandidate = {
  guidePosition: number;
  resolvedValue: number;
  distance: number;
  orientation: 'vertical' | 'horizontal';
};

type CanvasLayerItem =
  | {
      id: typeof BACKGROUND_LAYER_ID;
      kind: 'background';
      zIndex: number;
    }
  | {
      id: string;
      kind: 'element';
      zIndex: number;
      element: TemplateElement;
    };

function clampValue(value: number, minimum: number, maximum: number): number {
  return Math.min(Math.max(value, minimum), maximum);
}

function getClosestZoomOptionIndex(currentZoom: number): number {
  return ZOOM_OPTIONS.reduce((closestIndex, option, optionIndex) => {
    const currentDistance = Math.abs(option.value - currentZoom);
    const closestDistance = Math.abs(ZOOM_OPTIONS[closestIndex].value - currentZoom);
    return currentDistance < closestDistance ? optionIndex : closestIndex;
  }, 0);
}

function getNextZoomValue(currentZoom: number, direction: 'in' | 'out'): number {
  const closestZoomOptionIndex = getClosestZoomOptionIndex(currentZoom);
  const nextZoomOptionIndex = direction === 'in'
    ? Math.min(closestZoomOptionIndex + 1, ZOOM_OPTIONS.length - 1)
    : Math.max(closestZoomOptionIndex - 1, 0);

  return ZOOM_OPTIONS[nextZoomOptionIndex]?.value ?? currentZoom;
}

function getResolvedBackgroundLayerZIndex(background: TemplateLayout['background'], elements: TemplateElement[]): number {
  if (typeof background.zIndex === 'number') {
    return background.zIndex;
  }

  if (elements.length === 0) {
    return 0;
  }

  return Math.min(...elements.map(element => element.zIndex)) - 1;
}

function generateId() {
  return `el_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
}

function createDefaultLayout(): TemplateLayout {
  // 4×6英寸 300DPI = 1200×1800
  return {
    id: generateId(),
    name: '未命名模板',
    paperSize: { width: 101.6, height: 152.4 },
    resolution: 300,
    orientation: 'portrait',
    background: { type: 'color', value: '#ffffff' },
    elements: []
  };
}

function createDefaultElement(type: TemplateElement['type']): TemplateElement {
  const base = {
    id: generateId(),
    type,
    x: 100,
    y: 100,
    width: 200,
    height: 150,
    rotation: 0,
    opacity: 1,
    zIndex: 10,
    locked: false,
    visible: true,
  };

  switch (type) {
    case 'photo':
      return { ...base, width: 250, height: 180, props: { photoNumber: 1, cropMode: 'fill', borderRadius: 4 } as PhotoElementProps };
    case 'text':
      return { ...base, width: 300, height: 50, props: { content: '输入文字', fontFamily: 'Inter', fontSize: 24, fontWeight: 400, color: '#000000', textAlign: 'center', lineHeight: 1.4 } as TextElementProps };
    case 'shape':
      return { ...base, width: 150, height: 100, props: { shapeType: 'rectangle', fillColor: '#e0e0e0', strokeColor: '#000000', strokeWidth: 1, borderRadius: 0 } as ShapeElementProps };
    case 'image':
      return { ...base, width: 200, height: 200, props: { src: '/images/logo-placeholder.svg', alt: 'Logo' } as ImageElementProps };
    case 'qr_code':
      return { ...base, width: 120, height: 120, props: { url: 'https://www.baidu.com' } as QrCodeElementProps };
    case 'date':
      return { ...base, width: 200, height: 30, props: { format: 'YYYY-MM-DD' } as DateElementProps };
    case 'datetime':
      return { ...base, width: 250, height: 30, props: { format: 'YYYY-MM-DD HH:mm' } as DateElementProps };
    default:
      return { ...base, props: {} as ElementProps };
  }
}

// 绘图缩放比例（将300DPI物理像素映射到屏幕上可显示的尺寸）
const DISPLAY_SCALE = 0.45;
const SELECTED_TEMPLATE_SESSION_KEY = "aibooth.templateEditor.templateId";
const JUST_SAVED_TEMPLATE_SESSION_KEY = "aibooth.templates.justSavedTemplateId";

function isTemplateLayout(value: unknown): value is TemplateLayout {
  if (!value || typeof value !== "object") return false;
  const layout = value as Partial<TemplateLayout>;
  return Boolean(
    layout.paperSize &&
    typeof layout.paperSize.width === "number" &&
    typeof layout.paperSize.height === "number" &&
    typeof layout.resolution === "number" &&
    typeof layout.orientation === "string" &&
    layout.background &&
    Array.isArray(layout.elements)
  );
}

function parseLegacyArgbColor(value: string | null): string {
  if (!value?.startsWith("#")) return "#ffffff";
  const normalized = value.length === 9 ? `#${value.slice(3)}` : value;
  return /^#[0-9a-fA-F]{6}$/.test(normalized) ? normalized : "#ffffff";
}

function readNumberAttr(element: Element, attr: string, fallback: number): number {
  const value = Number(element.getAttribute(attr));
  return Number.isFinite(value) ? value : fallback;
}

function parseLegacyTemplateXml(xmlText: string): TemplateLayout {
  const doc = new DOMParser().parseFromString(xmlText, "application/xml");
  if (doc.querySelector("parsererror")) {
    throw new Error("模板 XML 格式无效");
  }

  const template = doc.querySelector("Template");
  if (!template) {
    throw new Error("未找到 Template 根节点");
  }

  const canvasWidth = readNumberAttr(template, "Width", 1200);
  const canvasHeight = readNumberAttr(template, "Height", 1800);
  const elements: TemplateElement[] = [];

  doc.querySelectorAll("Photo").forEach((node, index) => {
    elements.push({
      id: generateId(),
      type: "photo",
      x: readNumberAttr(node, "Left", 0),
      y: readNumberAttr(node, "Top", 0),
      width: readNumberAttr(node, "Width", 300),
      height: readNumberAttr(node, "Height", 200),
      rotation: readNumberAttr(node, "Rotation", 0),
      opacity: 1,
      zIndex: readNumberAttr(node, "ZIndex", index),
      locked: false,
      visible: true,
      props: {
        photoNumber: readNumberAttr(node, "PhotoNumber", index + 1),
        cropMode: node.getAttribute("KeepAspect") === "True" ? "fit" : "stretch",
        borderRadius: 0,
      } as PhotoElementProps,
    });
  });

  doc.querySelectorAll("Image").forEach((node, index) => {
    const imagePath = node.getAttribute("ImagePath") || "";
    elements.push({
      id: generateId(),
      type: "image",
      x: readNumberAttr(node, "Left", 0),
      y: readNumberAttr(node, "Top", 0),
      width: readNumberAttr(node, "Width", 300),
      height: readNumberAttr(node, "Height", 200),
      rotation: readNumberAttr(node, "Rotation", 0),
      opacity: 1,
      zIndex: readNumberAttr(node, "ZIndex", elements.length + index),
      locked: false,
      visible: true,
      props: {
        src: imagePath,
        alt: node.getAttribute("Name") || imagePath || "Imported image",
      } as ImageElementProps,
    });
  });

  return {
    id: generateId(),
    name: template.getAttribute("Name") || "导入模板",
    paperSize: {
      width: Number((canvasWidth * 25.4 / 300).toFixed(1)),
      height: Number((canvasHeight * 25.4 / 300).toFixed(1)),
    },
    resolution: 300,
    orientation: canvasWidth > canvasHeight ? "landscape" : "portrait",
    background: {
      type: "color",
      value: parseLegacyArgbColor(template.getAttribute("BackgroundColor")),
    },
    elements,
  };
}

function readImageFileAsDataUrl(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const fileReader = new FileReader();
    fileReader.onload = () => {
      if (typeof fileReader.result === "string") {
        resolve(fileReader.result);
        return;
      }
      reject(new Error("图片读取失败"));
    };
    fileReader.onerror = () => reject(new Error("图片读取失败"));
    fileReader.readAsDataURL(file);
  });
}

export function TemplateEditorScreen({ navigate }: { navigate: (s: Screen) => void }) {
  // ─── 状态 ───
  const { currentEvent } = useSettings();
  const {
    authToken,
    teamId: captureTeamId,
    setActivePrintTemplate,
    templateSelectionReturnScreen,
    setTemplateSelectionReturnScreen,
  } = useCaptureFlow();
  const undoRedo = useUndoRedo<TemplateLayout>(createDefaultLayout(), { maxHistory: 50 });
  const layout = undoRedo.present;

  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [zoom, setZoom] = useState(ZOOM_OPTIONS[1].value); // 默认50%
  const [zoomOpen, setZoomOpen] = useState(false);
  const [isPreview, setIsPreview] = useState(false);
  const [presetOpen, setPresetOpen] = useState(false);
  const [templateName, setTemplateName] = useState('未命名模板');
  const [editingName, setEditingName] = useState(false);
  const [savedTemplateId, setSavedTemplateId] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [isBackgroundLocked, setIsBackgroundLocked] = useState(false);
  const [isCanvasViewportHovered, setIsCanvasViewportHovered] = useState(false);
  const [interactionLayout, setInteractionLayout] = useState<TemplateLayout | null>(null);
  const [snapGuides, setSnapGuides] = useState<SnapGuide[]>([]);

  // 拖拽状态
  const [dragging, setDragging] = useState(false);
  const [resizing, setResizing] = useState<string | null>(null);
  const resizeDirRef = useRef<string>('');
  const dragStartRef = useRef({ x: 0, y: 0 });
  const interactionLayoutRef = useRef<TemplateLayout | null>(null);
  const interactionDidChangeRef = useRef(false);
  const canvasRef = useRef<HTMLDivElement>(null);
  const importInputRef = useRef<HTMLInputElement>(null);
  const backgroundImageInputRef = useRef<HTMLInputElement>(null);
  const elementImageInputRef = useRef<HTMLInputElement>(null);

  const zoomLabel = ZOOM_OPTIONS.find(z => z.value === zoom)?.label ?? "100%";
  const renderedLayout = interactionLayout ?? layout;

  const selectedElement = renderedLayout.elements.find(e => e.id === selectedIds[0]) || null;

  useEffect(() => {
    const templateId = sessionStorage.getItem(SELECTED_TEMPLATE_SESSION_KEY);
    const quickLayoutId = sessionStorage.getItem(TEMPLATE_EDITOR_QUICK_LAYOUT_SESSION_KEY);
    if (!templateId && !quickLayoutId) return;
    sessionStorage.removeItem(SELECTED_TEMPLATE_SESSION_KEY);
    sessionStorage.removeItem(TEMPLATE_EDITOR_QUICK_LAYOUT_SESSION_KEY);

    if (!templateId) {
      const preset = QUICK_PRINT_LAYOUTS.find(item => item.id === quickLayoutId);
      if (!preset) {
        showToast.error("未找到所选版式");
        return;
      }
      undoRedo.reset(createTemplateLayoutFromPrintPreset(layout.id, preset));
      setTemplateName(preset.name);
      setSavedTemplateId(null);
      setSelectedIds([]);
      return;
    }

    getTemplate(templateId, authToken ?? undefined)
      .then(template => {
        if (!isTemplateLayout(template.layers)) {
          showToast.error("模板数据结构无效");
          return;
        }
        const nextLayout = {
          ...template.layers,
          id: template.layers.id || template.id,
          name: template.name,
        };
        undoRedo.reset(nextLayout);
        setTemplateName(template.name);
        setSavedTemplateId(template.id);
        setSelectedIds([]);
      })
      .catch(err => {
        showToast.error(err instanceof Error ? err.message : "模板加载失败");
      });
  }, [authToken, layout.id, undoRedo]);

  // ─── 快捷键 ───
  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'z') {
        e.preventDefault();
        if (e.shiftKey) undoRedo.redo();
        else undoRedo.undo();
      }
      if ((e.ctrlKey || e.metaKey) && e.key === 'y') {
        e.preventDefault();
        undoRedo.redo();
      }
      if (e.key === 'Delete' || e.key === 'Backspace') {
        if (document.activeElement?.tagName === 'INPUT' || document.activeElement?.tagName === 'TEXTAREA') return;
        deleteSelected();
      }
      // 方向键微调
      if (['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight'].includes(e.key) && selectedIds.length > 0) {
        if (document.activeElement?.tagName === 'INPUT' || document.activeElement?.tagName === 'TEXTAREA') return;
        e.preventDefault();
        const delta = e.shiftKey ? 10 : 1;
        const dx = e.key === 'ArrowLeft' ? -delta : e.key === 'ArrowRight' ? delta : 0;
        const dy = e.key === 'ArrowUp' ? -delta : e.key === 'ArrowDown' ? delta : 0;
        moveSelected(dx, dy);
      }
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [selectedIds, layout]);

  // ─── 画布尺寸 ───
  const canvasPx = {
    width: Math.round(renderedLayout.paperSize.width * renderedLayout.resolution / 25.4),
    height: Math.round(renderedLayout.paperSize.height * renderedLayout.resolution / 25.4),
  };
  // 竖版时可能宽高对调
  const displayWidth = Math.round(canvasPx.width * DISPLAY_SCALE * zoom);
  const displayHeight = Math.round(canvasPx.height * DISPLAY_SCALE * zoom);

  const getLayoutSnapshot = useCallback((): TemplateLayout => ({
    ...renderedLayout,
    name: templateName.trim() || "未命名模板",
  }), [renderedLayout, templateName]);

  const resolveTeamId = useCallback(async () => {
    if (currentEvent?.teamId) return currentEvent.teamId;
    if (captureTeamId) return captureTeamId;
    const teams = await getMyTeams(authToken ?? undefined);
    return teams[0]?.id ?? null;
  }, [authToken, captureTeamId, currentEvent?.teamId]);

  // ─── 布局修改辅助函数 ───
  const updateLayout = useCallback((updater: (draft: TemplateLayout) => void) => {
    const draft = JSON.parse(JSON.stringify(interactionLayoutRef.current ?? renderedLayout));
    updater(draft);
    interactionLayoutRef.current = null;
    setInteractionLayout(null);
    undoRedo.set(draft);
  }, [renderedLayout, undoRedo]);

  const updateElement = useCallback((id: string, partial: Partial<TemplateElement>) => {
    const draft = JSON.parse(JSON.stringify(interactionLayoutRef.current ?? renderedLayout));
    const idx = draft.elements.findIndex((e: TemplateElement) => e.id === id);
    if (idx >= 0) {
      draft.elements[idx] = { ...draft.elements[idx], ...partial };
      interactionLayoutRef.current = null;
      setInteractionLayout(null);
      undoRedo.set(draft);
    }
  }, [renderedLayout, undoRedo]);

  const handleCanvasWheelZoom = useCallback((event: ReactWheelEvent<HTMLDivElement>) => {
    const currentCanvasViewport = canvasRef.current;
    const eventTarget = event.target;
    const isWheelInsideCanvasViewport = Boolean(
      currentCanvasViewport &&
      eventTarget instanceof Node &&
      currentCanvasViewport.contains(eventTarget)
    );

    if (!isCanvasViewportHovered || !isWheelInsideCanvasViewport || event.deltaY === 0) {
      return;
    }

    event.preventDefault();
    event.stopPropagation();
    setZoom(currentZoom => getNextZoomValue(currentZoom, event.deltaY < 0 ? 'in' : 'out'));
    setZoomOpen(false);
  }, [isCanvasViewportHovered]);

  // ─── 选中与图层操作 ───
  const selectElement = (id: string, multi: boolean) => {
    if (multi) {
      setSelectedIds(prev =>
        prev.includes(id) ? prev.filter(i => i !== id) : [...prev, id]
      );
    } else {
      setSelectedIds([id]);
    }
  };

  const deleteSelected = useCallback(() => {
    if (selectedIds.length === 0) return;
    const draft = JSON.parse(JSON.stringify(layout));
    draft.elements = draft.elements.filter((e: TemplateElement) => !selectedIds.includes(e.id));
    undoRedo.set(draft);
    setSelectedIds([]);
  }, [selectedIds, layout, undoRedo]);

  const duplicateSelected = () => {
    if (selectedIds.length === 0) return;
    const draft = JSON.parse(JSON.stringify(layout));
    const newElements: TemplateElement[] = [];
    selectedIds.forEach(sid => {
      const orig = draft.elements.find((e: TemplateElement) => e.id === sid);
      if (orig) {
        const clone = { ...orig, id: generateId(), x: orig.x + 20, y: orig.y + 20, zIndex: Math.max(...draft.elements.map((e: TemplateElement) => e.zIndex)) + 1 };
        newElements.push(clone);
      }
    });
    draft.elements = [...draft.elements, ...newElements];
    undoRedo.set(draft);
  };

  const toggleLock = (id: string) => {
    const el = layout.elements.find(e => e.id === id);
    if (el) updateElement(id, { locked: !el.locked });
  };

  const toggleVisibility = (id: string) => {
    const el = layout.elements.find(e => e.id === id);
    if (el) updateElement(id, { visible: !el.visible });
  };

  const moveLayer = (id: string, direction: 'up' | 'down') => {
    const draft = JSON.parse(JSON.stringify(layout));
    const resolvedBackgroundLayerZIndex = getResolvedBackgroundLayerZIndex(draft.background, draft.elements);
    const sortedCanvasLayers: CanvasLayerItem[] = [
      ...(draft.background.type === 'image'
        ? [{ id: BACKGROUND_LAYER_ID, kind: 'background', zIndex: resolvedBackgroundLayerZIndex } as CanvasLayerItem]
        : []),
      ...draft.elements.map((element: TemplateElement) => ({
        id: element.id,
        kind: 'element' as const,
        zIndex: element.zIndex,
        element,
      })),
    ].sort((leftLayer, rightLayer) => leftLayer.zIndex - rightLayer.zIndex);

    const idx = sortedCanvasLayers.findIndex(layer => layer.id === id);
    if (idx < 0) return;

    const swapTargetIndex = direction === 'up' ? idx + 1 : idx - 1;
    if (swapTargetIndex < 0 || swapTargetIndex >= sortedCanvasLayers.length) {
      return;
    }

    const currentLayer = sortedCanvasLayers[idx];
    const swapTargetLayer = sortedCanvasLayers[swapTargetIndex];
    const currentLayerZIndex = currentLayer.zIndex;
    const swapTargetLayerZIndex = swapTargetLayer.zIndex;

    if (currentLayer.kind === 'background') {
      draft.background.zIndex = swapTargetLayerZIndex;
    } else {
      const currentElement = draft.elements.find((element: TemplateElement) => element.id === currentLayer.id);
      if (currentElement) {
        currentElement.zIndex = swapTargetLayerZIndex;
      }
    }

    if (swapTargetLayer.kind === 'background') {
      draft.background.zIndex = currentLayerZIndex;
    } else {
      const swapTargetElement = draft.elements.find((element: TemplateElement) => element.id === swapTargetLayer.id);
      if (swapTargetElement) {
        swapTargetElement.zIndex = currentLayerZIndex;
      }
    }

    undoRedo.set(draft);
  };

  // ─── 选中元素移动 ───
  const moveSelected = (dx: number, dy: number) => {
    const draft = JSON.parse(JSON.stringify(layout));
    selectedIds.forEach(sid => {
      const el = draft.elements.find((e: TemplateElement) => e.id === sid);
      if (el && !el.locked) {
        el.x += dx;
        el.y += dy;
      }
    });
    undoRedo.set(draft);
  };

  // ─── 对齐 ───
  const alignElements = (dir: 'left' | 'center' | 'right' | 'top' | 'middle' | 'bottom') => {
    if (selectedIds.length < 2) return;
    const draft = JSON.parse(JSON.stringify(layout));
    const els = draft.elements.filter((e: TemplateElement) => selectedIds.includes(e.id) && !e.locked);
    if (els.length < 2) return;

    switch (dir) {
      case 'left': {
        const minX = Math.min(...els.map((e: TemplateElement) => e.x));
        els.forEach((e: TemplateElement) => { e.x = minX; });
        break;
      }
      case 'right': {
        const maxRight = Math.max(...els.map((e: TemplateElement) => e.x + e.width));
        els.forEach((e: TemplateElement) => { e.x = maxRight - e.width; });
        break;
      }
      case 'center': {
        const avgX = els.reduce((s: number, e: TemplateElement) => s + e.x + e.width / 2, 0) / els.length;
        els.forEach((e: TemplateElement) => { e.x = avgX - e.width / 2; });
        break;
      }
      case 'top': {
        const minY = Math.min(...els.map((e: TemplateElement) => e.y));
        els.forEach((e: TemplateElement) => { e.y = minY; });
        break;
      }
      case 'bottom': {
        const maxBottom = Math.max(...els.map((e: TemplateElement) => e.y + e.height));
        els.forEach((e: TemplateElement) => { e.y = maxBottom - e.height; });
        break;
      }
      case 'middle': {
        const avgY = els.reduce((s: number, e: TemplateElement) => s + e.y + e.height / 2, 0) / els.length;
        els.forEach((e: TemplateElement) => { e.y = avgY - e.height / 2; });
        break;
      }
    }
    undoRedo.set(draft);
  };

  // ─── 属性修改 ───
  const updateProp = (key: string, value: unknown) => {
    if (!selectedElement) return;
    const newProps = { ...selectedElement.props, [key]: value } as ElementProps;
    updateElement(selectedElement.id, { props: newProps });
  };

  const saveTemplate = useCallback(async () => {
    setIsSaving(true);
    try {
      const teamId = await resolveTeamId();
      if (!teamId) {
        showToast.error("未找到可保存模板的团队");
        return;
      }

      const snapshot = getLayoutSnapshot();
      const layers = snapshot as unknown as Record<string, unknown>;
      const validation = await validateTemplate(layers, authToken ?? undefined);
      if (!validation.valid) {
        showToast.error(validation.message || "模板结构校验失败");
        return;
      }

      const payload = {
        name: snapshot.name,
        description: "由模板编辑器保存",
        size: `${snapshot.paperSize.width}x${snapshot.paperSize.height}mm`,
        canvas_width: canvasPx.width,
        canvas_height: canvasPx.height,
        layers,
        is_public: false,
      };

      const saved = savedTemplateId
        ? await updateTemplate(savedTemplateId, payload, authToken ?? undefined)
        : await createTemplate({ ...payload, team_id: teamId }, authToken ?? undefined);

      setSavedTemplateId(saved.id);
      setTemplateName(saved.name);
      setActivePrintTemplate({
        id: saved.id,
        name: saved.name,
        layout: {
          ...snapshot,
          id: snapshot.id || saved.id,
          name: saved.name,
        },
      });
      const returnScreen = templateSelectionReturnScreen === "print" || templateSelectionReturnScreen === "camera"
        ? templateSelectionReturnScreen
        : null;

      if (returnScreen) {
        setTemplateSelectionReturnScreen(null);
        showToast.success(savedTemplateId ? "模板已更新并应用" : "模板已保存并应用");
        navigate(returnScreen);
      } else {
        sessionStorage.setItem(JUST_SAVED_TEMPLATE_SESSION_KEY, saved.id);
        showToast.success(savedTemplateId ? "模板已更新" : "模板已保存");
        navigate("templates");
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "模板保存失败";
      if (/401|unauthorized|未授权|not authenticated|login/i.test(errorMessage)) {
        showToast.error("请先登录后再保存模板");
      } else {
        showToast.error(errorMessage);
      }
    } finally {
      setIsSaving(false);
    }
  }, [
    authToken,
    canvasPx.height,
    canvasPx.width,
    getLayoutSnapshot,
    navigate,
    resolveTeamId,
    savedTemplateId,
    setActivePrintTemplate,
    setTemplateSelectionReturnScreen,
    templateSelectionReturnScreen,
  ]);

  // ─── 预设应用 ───
  const applyPreset = (presetIndex: number) => {
    const preset = TEMPLATE_PRESETS[presetIndex];
    const newLayout: TemplateLayout = {
      id: layout.id,
      name: preset.name,
      ...preset.layout,
    };
    // 重新生成所有元素ID
    newLayout.elements = newLayout.elements.map(el => ({ ...el, id: generateId() }));
    undoRedo.set(newLayout);
    setTemplateName(preset.name);
    setSelectedIds([]);
    setPresetOpen(false);
    showToast.success(`已应用预设: ${preset.name}`);
  };

  const applyPrintLayout = (preset: PrintLayoutPreset) => {
    undoRedo.set(createTemplateLayoutFromPrintPreset(layout.id, preset));
    setTemplateName(preset.name);
    setSavedTemplateId(null);
    setSelectedIds([]);
    showToast.success(`已应用版式: ${preset.name}`);
  };

  const importLegacyTemplate = async (file: File) => {
    try {
      const text = await file.text();
      const importedLayout = parseLegacyTemplateXml(text);
      undoRedo.reset(importedLayout);
      setTemplateName(importedLayout.name);
      setSavedTemplateId(null);
      setSelectedIds([]);
      showToast.success("旧版模板已导入");
    } catch (err) {
      showToast.error(err instanceof Error ? err.message : "模板导入失败");
    } finally {
      if (importInputRef.current) {
        importInputRef.current.value = "";
      }
    }
  };

  const importBackgroundImage = async (file: File) => {
    if (isBackgroundLocked) {
      showToast.info("底图已锁定，请先解锁后再替换");
      return;
    }

    try {
      const backgroundImageDataUrl = await readImageFileAsDataUrl(file);
      updateLayout(draftLayout => {
        draftLayout.background = {
          type: 'image',
          value: backgroundImageDataUrl,
        };
      });
      showToast.success("底图已导入，请继续拖放照片框定位拍照区域");
    } catch (err) {
      showToast.error(err instanceof Error ? err.message : "底图导入失败");
    } finally {
      if (backgroundImageInputRef.current) {
        backgroundImageInputRef.current.value = "";
      }
    }
  };

  const importSelectedImageElement = async (file: File) => {
    if (!selectedElement || selectedElement.type !== 'image') return;

    try {
      const imageDataUrl = await readImageFileAsDataUrl(file);
      updateElement(selectedElement.id, {
        props: {
          ...(selectedElement.props as ImageElementProps),
          src: imageDataUrl,
          alt: file.name || "Uploaded image",
        } as ImageElementProps,
      });
      showToast.success("装饰图片已更新");
    } catch (err) {
      showToast.error(err instanceof Error ? err.message : "装饰图片导入失败");
    } finally {
      if (elementImageInputRef.current) {
        elementImageInputRef.current.value = "";
      }
    }
  };

  const getCanvasSnapGuides = useCallback(() => ({
    vertical: [0, Math.round(canvasPx.width / 2), canvasPx.width],
    horizontal: [0, Math.round(canvasPx.height / 2), canvasPx.height],
  }), [canvasPx.height, canvasPx.width]);

  const getBestSnapCandidate = useCallback((
    candidates: SnapCandidate[],
  ) => {
    let bestCandidate: SnapCandidate | null = null;

    for (const candidate of candidates) {
      if (candidate.distance > SNAP_THRESHOLD) continue;
      if (!bestCandidate || candidate.distance < bestCandidate.distance) {
        bestCandidate = candidate;
      }
    }

    return bestCandidate;
  }, []);

  const snapMovePosition = useCallback((x: number, y: number, width: number, height: number) => {
    const guides = getCanvasSnapGuides();
    const verticalCandidate = getBestSnapCandidate(
      guides.vertical.flatMap(guidePosition => [
        { guidePosition, resolvedValue: guidePosition, distance: Math.abs(x - guidePosition), orientation: 'vertical' as const },
        { guidePosition, resolvedValue: guidePosition - width / 2, distance: Math.abs((x + width / 2) - guidePosition), orientation: 'vertical' as const },
        { guidePosition, resolvedValue: guidePosition - width, distance: Math.abs((x + width) - guidePosition), orientation: 'vertical' as const },
      ]),
    );
    const horizontalCandidate = getBestSnapCandidate(
      guides.horizontal.flatMap(guidePosition => [
        { guidePosition, resolvedValue: guidePosition, distance: Math.abs(y - guidePosition), orientation: 'horizontal' as const },
        { guidePosition, resolvedValue: guidePosition - height / 2, distance: Math.abs((y + height / 2) - guidePosition), orientation: 'horizontal' as const },
        { guidePosition, resolvedValue: guidePosition - height, distance: Math.abs((y + height) - guidePosition), orientation: 'horizontal' as const },
      ]),
    );

    return {
      x: verticalCandidate ? Math.round(verticalCandidate.resolvedValue) : x,
      y: horizontalCandidate ? Math.round(horizontalCandidate.resolvedValue) : y,
      guides: [
        ...(verticalCandidate ? [{ orientation: 'vertical' as const, position: verticalCandidate.guidePosition }] : []),
        ...(horizontalCandidate ? [{ orientation: 'horizontal' as const, position: horizontalCandidate.guidePosition }] : []),
      ],
    };
  }, [getBestSnapCandidate, getCanvasSnapGuides]);

  const snapResizeBounds = useCallback((
    nextElement: { x: number; y: number; width: number; height: number },
    resizeDirection: string,
  ) => {
    const guides = getCanvasSnapGuides();
    const nextGuides: SnapGuide[] = [];
    const rightEdge = nextElement.x + nextElement.width;
    const bottomEdge = nextElement.y + nextElement.height;

    if (resizeDirection.includes('e')) {
      const candidate = getBestSnapCandidate(
        guides.vertical.map(guidePosition => ({
          guidePosition,
          resolvedValue: guidePosition - nextElement.x,
          distance: Math.abs(rightEdge - guidePosition),
          orientation: 'vertical' as const,
        })),
      );
      if (candidate && candidate.resolvedValue >= MINIMUM_ELEMENT_SIZE) {
        nextElement.width = Math.round(candidate.resolvedValue);
        nextGuides.push({ orientation: 'vertical', position: candidate.guidePosition });
      }
    }

    if (resizeDirection.includes('w')) {
      const candidate = getBestSnapCandidate(
        guides.vertical.map(guidePosition => ({
          guidePosition,
          resolvedValue: guidePosition,
          distance: Math.abs(nextElement.x - guidePosition),
          orientation: 'vertical' as const,
        })),
      );
      if (candidate && rightEdge - candidate.resolvedValue >= MINIMUM_ELEMENT_SIZE) {
        nextElement.x = Math.round(candidate.resolvedValue);
        nextElement.width = rightEdge - nextElement.x;
        nextGuides.push({ orientation: 'vertical', position: candidate.guidePosition });
      }
    }

    if (resizeDirection.includes('s')) {
      const candidate = getBestSnapCandidate(
        guides.horizontal.map(guidePosition => ({
          guidePosition,
          resolvedValue: guidePosition - nextElement.y,
          distance: Math.abs(bottomEdge - guidePosition),
          orientation: 'horizontal' as const,
        })),
      );
      if (candidate && candidate.resolvedValue >= MINIMUM_ELEMENT_SIZE) {
        nextElement.height = Math.round(candidate.resolvedValue);
        nextGuides.push({ orientation: 'horizontal', position: candidate.guidePosition });
      }
    }

    if (resizeDirection.includes('n')) {
      const candidate = getBestSnapCandidate(
        guides.horizontal.map(guidePosition => ({
          guidePosition,
          resolvedValue: guidePosition,
          distance: Math.abs(nextElement.y - guidePosition),
          orientation: 'horizontal' as const,
        })),
      );
      if (candidate && bottomEdge - candidate.resolvedValue >= MINIMUM_ELEMENT_SIZE) {
        nextElement.y = Math.round(candidate.resolvedValue);
        nextElement.height = bottomEdge - nextElement.y;
        nextGuides.push({ orientation: 'horizontal', position: candidate.guidePosition });
      }
    }

    return nextGuides;
  }, [getBestSnapCandidate, getCanvasSnapGuides]);

  // ─── 添加新元素 ───
  const addElement = (type: TemplateElement['type']) => {
    const draft = JSON.parse(JSON.stringify(renderedLayout));
    const maxZ = draft.elements.length > 0 ? Math.max(...draft.elements.map((e: TemplateElement) => e.zIndex)) : 0;
    const newEl = createDefaultElement(type);
    newEl.zIndex = maxZ + 1;
    draft.elements.push(newEl);
    interactionLayoutRef.current = null;
    setInteractionLayout(null);
    undoRedo.set(draft);
    setSelectedIds([newEl.id]);
  };

  // ─── 画布鼠标事件（拖拽移动/缩放） ───
  const handleCanvasMouseDown = (e: React.MouseEvent, elId: string) => {
    e.preventDefault();

    // 如果有Shift键，进入多选模式
    if (e.shiftKey) {
      selectElement(elId, true);
      return;
    }
    // 检查点击的元素是否已选中
    if (!selectedIds.includes(elId)) {
      setSelectedIds([elId]);
    }
    // 检查是否为锁定的元素
    const el = renderedLayout.elements.find(el => el.id === elId);
    if (el?.locked) return;

    // 开始拖拽
    interactionDidChangeRef.current = false;
    setDragging(true);
    dragStartRef.current = { x: e.clientX, y: e.clientY };
    e.stopPropagation();
  };

  const handleResizeMouseDown = (e: React.MouseEvent, elId: string, dir: string) => {
    e.stopPropagation();
    e.preventDefault();
    interactionDidChangeRef.current = false;
    setResizing(elId);
    resizeDirRef.current = dir;
    dragStartRef.current = { x: e.clientX, y: e.clientY };
  };

  useEffect(() => {
    if (dragging || resizing || !interactionLayout || interactionLayoutRef.current) {
      return;
    }

    const committedLayoutMatchesInteractionLayout = JSON.stringify(layout) === JSON.stringify(interactionLayout);
    if (committedLayoutMatchesInteractionLayout) {
      setInteractionLayout(null);
    }
  }, [dragging, interactionLayout, layout, resizing]);

  useEffect(() => {
    if (!dragging && !resizing) return;

    const onMouseMove = (e: MouseEvent) => {
      const dx = (e.clientX - dragStartRef.current.x) / (DISPLAY_SCALE * zoom);
      const dy = (e.clientY - dragStartRef.current.y) / (DISPLAY_SCALE * zoom);
      dragStartRef.current = { x: e.clientX, y: e.clientY };

      if (dragging && selectedIds.length > 0) {
        const draft = JSON.parse(JSON.stringify(interactionLayoutRef.current ?? renderedLayout));
        const nextGuides: SnapGuide[] = [];
        selectedIds.forEach(sid => {
          const el = draft.elements.find((el: TemplateElement) => el.id === sid);
          if (el && !el.locked) {
            const maximumX = Math.max(0, canvasPx.width - el.width);
            const maximumY = Math.max(0, canvasPx.height - el.height);
            const nextX = clampValue(Math.round(el.x + dx), 0, maximumX);
            const nextY = clampValue(Math.round(el.y + dy), 0, maximumY);

            if (selectedIds.length === 1) {
              const snappedPosition = snapMovePosition(nextX, nextY, el.width, el.height);
              el.x = clampValue(snappedPosition.x, 0, maximumX);
              el.y = clampValue(snappedPosition.y, 0, maximumY);
              nextGuides.push(...snappedPosition.guides);
            } else {
              el.x = nextX;
              el.y = nextY;
            }
          }
        });
        setSnapGuides(nextGuides);
        interactionDidChangeRef.current = true;
        interactionLayoutRef.current = draft;
        setInteractionLayout(draft);
      }

      if (resizing) {
        const draft = JSON.parse(JSON.stringify(interactionLayoutRef.current ?? renderedLayout));
        const el = draft.elements.find((el: TemplateElement) => el.id === resizing);
        if (el && !el.locked) {
          const dir = resizeDirRef.current;
          const rightEdge = el.x + el.width;
          const bottomEdge = el.y + el.height;

          if (dir.includes('e')) {
            el.width = clampValue(
              Math.round(el.width + dx),
              MINIMUM_ELEMENT_SIZE,
              Math.max(MINIMUM_ELEMENT_SIZE, canvasPx.width - el.x),
            );
          }

          if (dir.includes('w')) {
            const nextLeft = clampValue(
              Math.round(el.x + dx),
              0,
              rightEdge - MINIMUM_ELEMENT_SIZE,
            );
            el.x = nextLeft;
            el.width = rightEdge - nextLeft;
          }

          if (dir.includes('s')) {
            el.height = clampValue(
              Math.round(el.height + dy),
              MINIMUM_ELEMENT_SIZE,
              Math.max(MINIMUM_ELEMENT_SIZE, canvasPx.height - el.y),
            );
          }

          if (dir.includes('n')) {
            const nextTop = clampValue(
              Math.round(el.y + dy),
              0,
              bottomEdge - MINIMUM_ELEMENT_SIZE,
            );
            el.y = nextTop;
            el.height = bottomEdge - nextTop;
          }

          const snappedGuides = snapResizeBounds(el, dir);
          setSnapGuides(snappedGuides);
          interactionDidChangeRef.current = true;
          interactionLayoutRef.current = draft;
          setInteractionLayout(draft);
        }
      }
    };

    const onMouseUp = () => {
      const finalInteractionLayout = interactionLayoutRef.current;
      setDragging(false);
      setResizing(null);
      setSnapGuides([]);

      if (interactionDidChangeRef.current && finalInteractionLayout) {
        undoRedo.set(finalInteractionLayout);
      } else {
        setInteractionLayout(null);
      }

      interactionLayoutRef.current = null;
      interactionDidChangeRef.current = false;
    };

    window.addEventListener('mousemove', onMouseMove);
    window.addEventListener('mouseup', onMouseUp);
    return () => {
      window.removeEventListener('mousemove', onMouseMove);
      window.removeEventListener('mouseup', onMouseUp);
    };
  }, [canvasPx.height, canvasPx.width, dragging, renderedLayout, resizing, selectedIds, snapMovePosition, snapResizeBounds, undoRedo, zoom]);

  // ─── Canvas背景点击取消选中 ───
  const handleCanvasBackgroundClick = () => {
    setSelectedIds([]);
    setSnapGuides([]);
  };

  // ─── 渲染元素───
  const renderElement = (el: TemplateElement) => {
    if (!el.visible) return null;
    const isSelected = selectedIds.includes(el.id);
    const style: React.CSSProperties = {
      position: 'absolute',
      left: el.x * DISPLAY_SCALE * zoom,
      top: el.y * DISPLAY_SCALE * zoom,
      width: el.width * DISPLAY_SCALE * zoom,
      height: el.height * DISPLAY_SCALE * zoom,
      transform: `rotate(${el.rotation}deg)`,
      opacity: el.opacity,
      zIndex: el.zIndex,
      border: isSelected ? '2px solid #3b82f6' : '1px solid transparent',
      cursor: el.locked ? 'default' : 'move',
      boxSizing: 'border-box' as const,
      overflow: 'hidden',
      userSelect: 'none' as const,
      touchAction: 'none' as const,
    };

    const innerStyle: React.CSSProperties = {
      width: '100%',
      height: '100%',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
    };

    let content: React.ReactNode;
    const resizeHandleTouchSize = Math.max(18, 20 / Math.max(zoom, 0.5));
    const resizeHandleVisualSize = Math.max(8, 10 / Math.max(zoom, 0.75));
    const shouldShowCompactPhotoCaption = el.width * DISPLAY_SCALE * zoom >= 96 && el.height * DISPLAY_SCALE * zoom >= 72;
    const shouldShowPhotoDragBar = el.width * DISPLAY_SCALE * zoom >= 110;

    switch (el.type) {
      case 'photo': {
        const pp = el.props as PhotoElementProps;
        const photoLabel = `照片 ${pp.photoNumber}`;
        const br = (pp.borderRadius || 0) * DISPLAY_SCALE * zoom;
        const frameBorderColor = isSelected ? '#60a5fa' : '#38bdf8';
        const frameBackgroundColor = isPreview ? 'rgba(255,255,255,0.08)' : 'rgba(56,189,248,0.12)';
        content = (
          <div style={{
            ...innerStyle,
            background: frameBackgroundColor,
            borderRadius: br,
            border: `2px dashed ${frameBorderColor}`,
            boxShadow: 'inset 0 0 0 1px rgba(255,255,255,0.35)',
          }}>
            <div style={{
              display: 'flex', flexDirection: 'column',
              alignItems: 'center', justifyContent: 'center',
              color: '#0f172a', fontSize: 10 * zoom,
              textAlign: 'center',
              padding: `${8 * zoom}px`,
            }}>
              <div style={{ fontSize: 18 * zoom, lineHeight: 1 }}>&#128247;</div>
              <div style={{ marginTop: 4 * zoom, fontWeight: 700 }}>{photoLabel}</div>
              {shouldShowCompactPhotoCaption && (
                <div style={{ fontSize: 8 * zoom, opacity: 0.55, marginTop: 2 * zoom }}>{pp.cropMode}</div>
              )}
            </div>
          </div>
        );
        break;
      }
      case 'text': {
        const tp = el.props as TextElementProps;
        content = (
          <div style={{
            ...innerStyle,
            fontFamily: tp.fontFamily,
            fontSize: (tp.fontSize || 14) * DISPLAY_SCALE * zoom,
            fontWeight: tp.fontWeight || 400,
            color: tp.color || '#000',
            textAlign: tp.textAlign || 'left',
            lineHeight: tp.lineHeight || 1.4,
            whiteSpace: 'pre-wrap',
            wordBreak: 'break-word',
            padding: '4px',
          }}>
            {tp.content || '文字'}
          </div>
        );
        break;
      }
      case 'shape': {
        const sp = el.props as ShapeElementProps;
        const borderRadius = (sp.shapeType === 'ellipse') ? '50%' : (sp.borderRadius || 0);
        content = (
          <div style={{
            ...innerStyle,
            background: sp.fillColor || '#e0e0e0',
            border: `${sp.strokeWidth || 0}px solid ${sp.strokeColor || '#000'}`,
            borderRadius,
          }}>
            {sp.shapeType === 'star' && <span style={{ fontSize: 24 * zoom }}>&#11088;</span>}
            {sp.shapeType === 'line' && (
              <div style={{ width: '100%', height: sp.strokeWidth || 2, background: sp.strokeColor || '#000', borderRadius: 1 }} />
            )}
          </div>
        );
        break;
      }
      case 'qr_code': {
        const qp = el.props as QrCodeElementProps;
        content = (
          <div style={{ ...innerStyle, background: '#fff', flexDirection: 'column', gap: 2 }}>
            <div style={{ fontSize: 10 * zoom, color: '#999' }}>QR Code</div>
            <div style={{ fontSize: 6 * zoom, color: '#bbb' }}>{qp.url}</div>
          </div>
        );
        break;
      }
      case 'date':
      case 'datetime': {
        const dp = el.props as DateElementProps;
        const display = (() => {
          const now = new Date();
          const fmt = dp.format || 'YYYY-MM-DD';
          return fmt
            .replace('YYYY', String(now.getFullYear()))
            .replace('MM', String(now.getMonth() + 1).padStart(2, '0'))
            .replace('DD', String(now.getDate()).padStart(2, '0'))
            .replace('HH', String(now.getHours()).padStart(2, '0'))
            .replace('mm', String(now.getMinutes()).padStart(2, '0'));
        })();
        content = (
          <div style={{
            ...innerStyle,
            fontFamily: 'monospace',
            fontSize: 14 * DISPLAY_SCALE * zoom,
            color: '#333',
            fontWeight: 600,
          }}>
            {display}
          </div>
        );
        break;
      }
      case 'image': {
        const ip = el.props as ImageElementProps;
        content = (
          <div style={{ ...innerStyle, background: '#f5f5f5', fontSize: 10 * zoom, color: '#999' }}>
            {ip.src ? (
              <img
                src={ip.src}
                alt={ip.alt || 'Image'}
                style={{ width: '100%', height: '100%', objectFit: 'fill' }}
              />
            ) : (
              <div style={{ textAlign: 'center' }}>
                <div>&#128444;</div>
                <div style={{ fontSize: 8 * zoom }}>Image</div>
              </div>
            )}
          </div>
        );
        break;
      }
      default:
        content = (
          <div style={{ ...innerStyle, background: '#f0f0f0', color: '#999', fontSize: 10 * zoom }}>
            {el.type}
          </div>
        );
    }

    return (
      <div
        key={el.id}
        style={style}
        onMouseDown={(e) => handleCanvasMouseDown(e, el.id)}
      >
        {content}
        {isSelected && !isPreview && el.type === 'photo' && shouldShowPhotoDragBar && (
          <div
            style={{
              position: 'absolute',
              left: '50%',
              top: -12,
              transform: 'translateX(-50%)',
              width: Math.max(72, Math.min(el.width * DISPLAY_SCALE * zoom * 0.45, 140)),
              height: 18,
              borderRadius: 999,
              background: 'rgba(15, 23, 42, 0.9)',
              border: '1px solid rgba(96, 165, 250, 0.65)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: 6,
              color: '#dbeafe',
              fontSize: Math.max(9, 10 / Math.max(zoom, 0.75)),
              cursor: 'grab',
              boxShadow: '0 4px 12px rgba(15,23,42,0.28)',
            }}
            onMouseDown={(event) => handleCanvasMouseDown(event, el.id)}
          >
            <Move size={10} />
            拖动条
          </div>
        )}
        {isSelected && !isPreview && (
          <div
            style={{
              position: 'absolute',
              left: '50%',
              top: -24,
              transform: 'translateX(-50%)',
              padding: '2px 8px',
              borderRadius: 999,
              background: 'rgba(15, 23, 42, 0.82)',
              color: '#e2e8f0',
              fontSize: Math.max(9, 10 / Math.max(zoom, 0.75)),
              whiteSpace: 'nowrap',
              pointerEvents: 'none',
              boxShadow: '0 2px 8px rgba(0,0,0,0.25)',
            }}
          >
            {Math.round(el.width)} x {Math.round(el.height)}
          </div>
        )}
        {/* 缩放手柄 */}
        {isSelected && !isPreview && (
          <>
            {['nw', 'n', 'ne', 'e', 'se', 's', 'sw', 'w'].map(dir => (
              <div key={dir}
                style={{
                  position: 'absolute',
                  width: resizeHandleTouchSize,
                  height: resizeHandleTouchSize,
                  background: 'transparent',
                  cursor: `${dir}-resize`,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  ...(dir.includes('n') ? { top: -resizeHandleTouchSize / 2 } : {}),
                  ...(dir.includes('s') ? { bottom: -resizeHandleTouchSize / 2 } : {}),
                  ...(dir.includes('w') ? { left: -resizeHandleTouchSize / 2 } : {}),
                  ...(dir.includes('e') ? { right: -resizeHandleTouchSize / 2 } : {}),
                  ...(!dir.includes('n') && !dir.includes('s') ? { top: '50%', marginTop: -resizeHandleTouchSize / 2 } : {}),
                  ...(!dir.includes('w') && !dir.includes('e') ? { left: '50%', marginLeft: -resizeHandleTouchSize / 2 } : {}),
                }}
                onMouseDown={(e) => handleResizeMouseDown(e, el.id, dir)}
              >
                <div
                  style={{
                    width: resizeHandleVisualSize,
                    height: resizeHandleVisualSize,
                    background: '#3b82f6',
                    border: '1px solid white',
                    borderRadius: dir.length === 2 ? '999px' : 3,
                    boxShadow: '0 1px 4px rgba(0,0,0,0.25)',
                  }}
                />
              </div>
            ))}
          </>
        )}
      </div>
    );
  };

  // ─── 排序后的元素列表 ───
  const sortedElements = [...renderedLayout.elements].sort((a, b) => a.zIndex - b.zIndex);
  const hasPhotoFrameElements = renderedLayout.elements.some(element => element.type === 'photo');
  const hasImageBackground = renderedLayout.background.type === 'image';
  const visibleLayerCount = renderedLayout.elements.length + (hasImageBackground ? 1 : 0);
  const resolvedBackgroundLayerZIndex = getResolvedBackgroundLayerZIndex(renderedLayout.background, renderedLayout.elements);
  const sortedCanvasLayers: CanvasLayerItem[] = [
    ...(hasImageBackground
      ? [{ id: BACKGROUND_LAYER_ID, kind: 'background', zIndex: resolvedBackgroundLayerZIndex } as CanvasLayerItem]
      : []),
    ...sortedElements.map(element => ({
      id: element.id,
      kind: 'element' as const,
      zIndex: element.zIndex,
      element,
    })),
  ].sort((leftLayer, rightLayer) => leftLayer.zIndex - rightLayer.zIndex);

  // ─── 渲染 ───
  return (
    <div className="flex-1 flex overflow-hidden min-w-0">
      {/* ─── 预设选择对话框 ─── */}
      <AnimatePresence>
        {presetOpen && (
          <motion.div
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/60"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => setPresetOpen(false)}
          >
            <motion.div
              className="bg-[#1a1a2e] border border-white/10 rounded-2xl p-6 w-[700px] max-h-[80vh] overflow-y-auto"
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              onClick={e => e.stopPropagation()}
            >
              <h3 className="text-sm font-semibold text-white mb-4">选择预设布局</h3>
              <div className="grid grid-cols-3 gap-4">
                {TEMPLATE_PRESETS.map((preset, i) => (
                  <button
                    key={preset.id}
                    className="rounded-xl p-4 text-left bg-white/5 hover:bg-white/10 border border-white/5 hover:border-violet-500/40 transition-all"
                    onClick={() => applyPreset(i)}
                  >
                    <div className="aspect-[2/5] bg-white/5 rounded-lg mb-3 flex items-center justify-center overflow-hidden">
                      <div className="text-3xl text-white/20">
                        <LayoutTemplate size={32} />
                      </div>
                    </div>
                    <div className="text-xs font-medium text-white">{preset.name}</div>
                    <div className="text-[10px] text-white/40 mt-0.5">{preset.description}</div>
                  </button>
                ))}
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ─── 左侧: 元素库 ─── */}
      <GlassCard className="w-48 shrink-0 rounded-none border-r border-white/5 flex flex-col overflow-hidden">
        <div className="px-4 py-3 border-b border-white/5">
          <div className="text-xs font-semibold text-white/60 uppercase tracking-wider">元素库</div>
        </div>
        <div className="flex-1 overflow-y-auto p-3 space-y-3">
          {!hasPhotoFrameElements && (
            <div className="rounded-xl border border-emerald-500/15 bg-white/5 p-3">
              <div className="flex items-center gap-2 text-xs font-semibold text-white">
                <LayoutTemplate size={14} />
                {layout.background.type === 'image' ? '底图已就绪' : '开始创建模板'}
              </div>
              <div className="mt-2 text-[10px] leading-5 text-white/45">
                {layout.background.type === 'image'
                  ? '先添加照片框，再拖动到出片区域。'
                  : '先上传底图，再添加照片框定义拍照区域。'}
              </div>
              <div className="mt-3 grid grid-cols-1 gap-2">
                <button
                  className="rounded-lg border border-emerald-500/20 bg-emerald-500/10 px-3 py-2 text-left text-[10px] text-emerald-300 hover:bg-emerald-500/15"
                  onClick={() => backgroundImageInputRef.current?.click()}
                >
                  <div className="font-medium">上传底图</div>
                  <div className="mt-0.5 text-emerald-200/70">导入 PNG/JPG 作为模板背景</div>
                </button>
                <button
                  className="rounded-lg border border-sky-500/20 bg-sky-500/10 px-3 py-2 text-left text-[10px] text-sky-300 hover:bg-sky-500/15"
                  onClick={() => addElement('photo')}
                >
                  <div className="font-medium">添加照片框</div>
                  <div className="mt-0.5 text-sky-200/70">拖动缩放到拍照区域</div>
                </button>
                <button
                  className="rounded-lg border border-violet-500/20 bg-violet-500/10 px-3 py-2 text-left text-[10px] text-violet-300 hover:bg-violet-500/15"
                  onClick={() => setPresetOpen(true)}
                >
                  <div className="font-medium">查看预设布局</div>
                  <div className="mt-0.5 text-violet-200/70">如果不想从零开始，可以直接套用预设</div>
                </button>
              </div>
            </div>
          )}

          <div>
            <div className="text-[10px] text-white/30 uppercase mb-2">添加元素</div>
            <div className="space-y-1">
              {[
                { type: 'photo' as const, icon: ImageIcon, label: '照片框' },
                { type: 'image' as const, icon: Upload, label: '装饰图片' },
                { type: 'text' as const, icon: TypeIcon, label: '文本' },
                { type: 'shape' as const, icon: Square, label: '形状' },
                { type: 'qr_code' as const, icon: ScanQrCode, label: '二维码' },
                { type: 'date' as const, icon: Calendar, label: '日期/时间' },
              ].map(item => (
                <button
                  key={item.type}
                  className="w-full flex items-center gap-2 px-3 py-2 rounded-lg bg-white/5 hover:bg-white/15 text-xs text-white/60 hover:text-white/90 transition-colors"
                  onClick={() => addElement(item.type)}
                >
                  <item.icon size={13} />
                  {item.label}
                  <Plus size={10} className="ml-auto text-white/20" />
                </button>
              ))}
            </div>
          </div>
          <div>
            <div className="text-[10px] text-white/30 uppercase mb-2">导入</div>
            <input
              ref={importInputRef}
              type="file"
              accept=".xml,text/xml,application/xml"
              className="hidden"
              onChange={event => {
                const file = event.target.files?.[0];
                if (file) void importLegacyTemplate(file);
              }}
            />
            <button
              className="w-full flex items-center gap-2 px-3 py-2 rounded-lg bg-white/5 hover:bg-white/15 text-xs text-white/60 hover:text-white/90 transition-colors"
              onClick={() => importInputRef.current?.click()}
            >
              <Upload size={13} />
              旧版 template.xml
            </button>
          </div>
          <div>
            <div className="text-[10px] text-white/30 uppercase mb-2">背景</div>
            <input
              ref={backgroundImageInputRef}
              type="file"
              accept="image/png,image/jpeg,image/webp,image/gif"
              className="hidden"
              onChange={event => {
                const file = event.target.files?.[0];
                if (file) void importBackgroundImage(file);
              }}
            />
            <div className="space-y-1">
              <button
                className={`w-full flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs transition-colors border ${isBackgroundLocked ? "bg-amber-500/10 border-amber-500/20 text-amber-300 hover:bg-amber-500/20" : "bg-white/5 border-white/10 text-white/60 hover:bg-white/10 hover:text-white/80"}`}
                onClick={() => setIsBackgroundLocked(value => !value)}
              >
                <Lock size={13} />
                {isBackgroundLocked ? "底图已锁定" : "锁定底图"}
              </button>
              <button
                className="w-full flex items-center gap-2 px-3 py-1.5 rounded-lg bg-emerald-500/10 hover:bg-emerald-500/20 text-xs text-emerald-300 hover:text-emerald-200 transition-colors border border-emerald-500/20 disabled:opacity-50 disabled:cursor-not-allowed"
                onClick={() => backgroundImageInputRef.current?.click()}
                disabled={isBackgroundLocked}
              >
                <Upload size={13} />
                上传底图
              </button>
              {layout.background.type === 'image' && (
                <button
                  className="w-full flex items-center gap-2 px-3 py-1.5 rounded-lg bg-white/5 hover:bg-white/10 text-xs text-white/60 hover:text-white/80 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  onClick={() => updateLayout(draftLayout => { draftLayout.background = { type: 'color', value: '#ffffff' }; })}
                  disabled={isBackgroundLocked}
                >
                  <Trash2 size={13} />
                  移除底图
                </button>
              )}
              {[
                { color: '#ffffff', label: '白色' },
                { color: '#f5f5f5', label: '浅灰' },
                { color: '#000000', label: '黑色' },
                { color: '#ffe4e6', label: '粉色' },
              ].map(bg => (
                <button
                  key={bg.color}
                  className="w-full flex items-center gap-2 px-3 py-1.5 rounded-lg bg-white/5 hover:bg-white/10 text-xs text-white/60 hover:text-white/80 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  onClick={() => updateLayout(d => { d.background = { type: 'color', value: bg.color }; })}
                  disabled={isBackgroundLocked}
                >
                  <div className="w-3 h-3 rounded border border-white/10" style={{ background: bg.color }} />
                  {bg.label}
                </button>
              ))}
            </div>
          </div>
        </div>
      </GlassCard>

      {/* ─── 中间: 画布 + 工具栏 ─── */}
      <div className="flex-1 min-w-0 flex flex-col bg-[#0a0a1a]">
        {/* 顶部工具栏 */}
        <div className="flex items-center justify-between px-4 py-2 border-b border-white/5">
          <div className="flex items-center gap-2">
            <button onClick={() => navigate("templates")} className="text-xs text-white/40 hover:text-white/70 flex items-center gap-1">
              <ArrowLeft size={14} />
              返回
            </button>
            <span className="text-xs text-white/20">/</span>
            {editingName ? (
              <input
                className="text-xs bg-white/10 border border-white/20 rounded px-2 py-0.5 text-white outline-none"
                value={templateName}
                onChange={e => setTemplateName(e.target.value)}
                onBlur={() => { setEditingName(false); updateLayout(d => { d.name = templateName; }); }}
                onKeyDown={e => { if (e.key === 'Enter') { setEditingName(false); updateLayout(d => { d.name = templateName; }); } }}
                autoFocus
              />
            ) : (
              <button onClick={() => setEditingName(true)} className="text-xs text-white/70 hover:text-white">
                {templateName}
              </button>
            )}
          </div>
          <div className="flex items-center gap-2">
            <div className="relative flex items-center gap-1 bg-white/5 rounded-lg px-2 py-1 cursor-pointer"
              onClick={() => setZoomOpen(o => !o)}>
              <span className="text-xs text-white/40">{zoomLabel}</span>
              <ChevronDown size={12} className="text-white/30" />
              {zoomOpen && (
                <div className="absolute top-full right-0 mt-1 bg-[#1a1a2e] border border-white/10 rounded-lg py-1 z-10 min-w-[100px]">
                  {ZOOM_OPTIONS.map(z => (
                    <button key={z.label}
                      className={`w-full px-3 py-1.5 text-xs text-left hover:bg-white/10 transition-colors ${zoom === z.value ? "text-violet-400" : "text-white/60"}`}
                      onClick={e => { e.stopPropagation(); setZoom(z.value); setZoomOpen(false); }}>
                      {z.label}
                    </button>
                  ))}
                </div>
              )}
            </div>
            <GlowBtn size="sm" variant="ghost"
              onClick={() => setIsPreview(p => !p)}
              className={isPreview ? "ring-1 ring-violet-500/50" : ""}>
              <Eye size={13} />{isPreview ? "退出预览" : "预览"}
            </GlowBtn>
            <GlowBtn size="sm" variant="primary" onClick={saveTemplate} disabled={isSaving}>
              <Save size={13} />{isSaving ? "保存中" : savedTemplateId ? "更新模板" : "保存模板"}
            </GlowBtn>
            <GlowBtn size="sm" variant="primary"
              onClick={() => {
                const json = JSON.stringify(getLayoutSnapshot(), null, 2);
                const blob = new Blob([json], { type: 'application/json' });
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `${templateName}.json`;
                a.click();
                URL.revokeObjectURL(url);
                showToast.success("模板已导出");
              }}>
              <Download size={13} />导出
            </GlowBtn>
          </div>
        </div>

        {/* 工具栏 */}
        <div className="flex items-center gap-1 px-4 py-2 border-b border-white/5">
          {/* 撤销/重做 */}
          <button
            className={`p-2 rounded-lg transition-colors ${undoRedo.canUndo ? "hover:bg-white/10 text-white/70" : "text-white/20 cursor-not-allowed"}`}
            onClick={() => undoRedo.undo()} disabled={!undoRedo.canUndo} title="撤销 (Ctrl+Z)">
            <Undo2 size={14} />
          </button>
          <button
            className={`p-2 rounded-lg transition-colors ${undoRedo.canRedo ? "hover:bg-white/10 text-white/70" : "text-white/20 cursor-not-allowed"}`}
            onClick={() => undoRedo.redo()} disabled={!undoRedo.canRedo} title="重做 (Ctrl+Y)">
            <Redo2 size={14} />
          </button>
          <div className="h-4 w-px bg-white/10 mx-1" />

          {/* 复制/删除 */}
          <button className="p-2 rounded-lg hover:bg-white/10 text-white/40 hover:text-white/70 transition-colors"
            onClick={duplicateSelected} title="复制选中元素">
            <Copy size={14} />
          </button>
          <button className="p-2 rounded-lg hover:bg-red-500/10 text-white/40 hover:text-red-400 transition-colors"
            onClick={deleteSelected} title="删除选中元素 (Delete)">
            <Trash2 size={14} />
          </button>
          <div className="h-4 w-px bg-white/10 mx-1" />

          {/* 对齐 */}
          <span className="text-[10px] text-white/30 mr-1">对齐:</span>
          <button className="p-1.5 rounded hover:bg-white/10 text-white/40 hover:text-white/70 transition-colors text-[10px]"
            onClick={() => alignElements('left')} title="左对齐">左</button>
          <button className="p-1.5 rounded hover:bg-white/10 text-white/40 hover:text-white/70 transition-colors text-[10px]"
            onClick={() => alignElements('center')} title="水平居中">中</button>
          <button className="p-1.5 rounded hover:bg-white/10 text-white/40 hover:text-white/70 transition-colors text-[10px]"
            onClick={() => alignElements('right')} title="右对齐">右</button>
          <div className="w-px h-3 bg-white/10" />
          <button className="p-1.5 rounded hover:bg-white/10 text-white/40 hover:text-white/70 transition-colors text-[10px]"
            onClick={() => alignElements('top')} title="顶对齐">顶</button>
          <button className="p-1.5 rounded hover:bg-white/10 text-white/40 hover:text-white/70 transition-colors text-[10px]"
            onClick={() => alignElements('middle')} title="垂直居中">中</button>
          <button className="p-1.5 rounded hover:bg-white/10 text-white/40 hover:text-white/70 transition-colors text-[10px]"
            onClick={() => alignElements('bottom')} title="底对齐">底</button>
        </div>

        {/* 画布区域 */}
        <div
          ref={canvasRef}
          className="flex-1 flex items-center justify-center p-6 overflow-auto"
          onWheel={handleCanvasWheelZoom}
          onMouseEnter={() => setIsCanvasViewportHovered(true)}
          onMouseLeave={() => setIsCanvasViewportHovered(false)}
          style={{
            background: `
              linear-gradient(45deg, rgba(255,255,255,0.02) 25%, transparent 25%),
              linear-gradient(-45deg, rgba(255,255,255,0.02) 25%, transparent 25%),
              linear-gradient(45deg, transparent 75%, rgba(255,255,255,0.02) 75%),
              linear-gradient(-45deg, transparent 75%, rgba(255,255,255,0.02) 75%)
            `,
            backgroundSize: '20px 20px',
            backgroundPosition: '0 0, 0 10px, 10px -10px, -10px 0px',
          }}
          onClick={handleCanvasBackgroundClick}
        >
          {/* 画布 */}
          <div
            className="relative shadow-2xl"
            style={{
              width: displayWidth,
              height: displayHeight,
              background: renderedLayout.background.type === 'color' ? renderedLayout.background.value : '#ffffff',
              overflow: 'hidden',
            }}
          >
            {/* 出血线 (内缩3%) */}
            {!isPreview && (
              <div
                className="absolute inset-0 pointer-events-none"
                style={{
                  border: '1px dashed rgba(255,0,0,0.3)',
                  margin: `${displayHeight * 0.03}px ${displayWidth * 0.03}px`,
                  borderRadius: 2,
                }}
              />
            )}

            {/* 渲染元素 */}
            {sortedCanvasLayers.map(layer => {
              if (layer.kind === 'background') {
                return (
                  <img
                    key={layer.id}
                    src={renderedLayout.background.value}
                    alt="模板底图"
                    className="absolute inset-0 w-full h-full pointer-events-none select-none"
                    style={{ objectFit: 'fill' }}
                    draggable={false}
                  />
                );
              }

              return renderElement(layer.element);
            })}

            {!isPreview && snapGuides.map((guide, index) => (
              <div
                key={`${guide.orientation}-${guide.position}-${index}`}
                className="absolute pointer-events-none"
                style={guide.orientation === 'vertical'
                  ? {
                      left: guide.position * DISPLAY_SCALE * zoom,
                      top: 0,
                      width: 1,
                      height: '100%',
                      background: 'rgba(96, 165, 250, 0.95)',
                      boxShadow: '0 0 0 1px rgba(191, 219, 254, 0.18)',
                    }
                  : {
                      top: guide.position * DISPLAY_SCALE * zoom,
                      left: 0,
                      height: 1,
                      width: '100%',
                      background: 'rgba(96, 165, 250, 0.95)',
                      boxShadow: '0 0 0 1px rgba(191, 219, 254, 0.18)',
                    }}
              />
            ))}

            {/* 预览模式遮罩 */}
            {isPreview && <div className="absolute inset-0 pointer-events-none" />}
          </div>
        </div>
      </div>

      {/* ─── 右侧: 图层 + 属性 ─── */}
      <GlassCard className="w-52 shrink-0 rounded-none border-l border-white/5 flex flex-col overflow-hidden">
        {/* 图层标题 */}
        <div className="px-4 py-3 border-b border-white/5">
          <div className="text-xs font-semibold text-white/60 uppercase tracking-wider">
            图层 ({visibleLayerCount})
          </div>
        </div>

        {/* 图层列表 */}
        <div className="flex-1 overflow-y-auto p-2 space-y-0.5" style={{ maxHeight: '40%' }}>
          {sortedCanvasLayers.map(layer => {
            if (layer.kind === 'background') {
              return (
                <div
                  key={layer.id}
                  className="flex items-center gap-1 px-2 py-1.5 rounded-lg text-xs text-emerald-300 bg-emerald-500/10 border border-emerald-500/15 group"
                >
                  <GripVertical size={10} className="text-emerald-300/40 shrink-0" />
                  <span className="flex-1 truncate">底图</span>
                  <div className="hidden group-hover:flex items-center gap-0.5">
                    <button
                      className="p-0.5 rounded hover:bg-white/10 text-emerald-300/70 disabled:opacity-50 disabled:cursor-not-allowed"
                      onClick={() => moveLayer(BACKGROUND_LAYER_ID, 'up')}
                      title="上移"
                      disabled={sortedCanvasLayers[sortedCanvasLayers.length - 1]?.id === BACKGROUND_LAYER_ID}
                    >
                      <ChevronUp size={10} />
                    </button>
                    <button
                      className="p-0.5 rounded hover:bg-white/10 text-emerald-300/70 disabled:opacity-50 disabled:cursor-not-allowed"
                      onClick={() => moveLayer(BACKGROUND_LAYER_ID, 'down')}
                      title="下移"
                      disabled={sortedCanvasLayers[0]?.id === BACKGROUND_LAYER_ID}
                    >
                      <ChevronDown size={10} />
                    </button>
                    <button
                      className={`p-0.5 rounded hover:bg-white/10 ${isBackgroundLocked ? 'text-amber-400' : 'text-emerald-300/70'}`}
                      onClick={() => setIsBackgroundLocked(value => !value)}
                      title={isBackgroundLocked ? '解锁底图' : '锁定底图'}
                    >
                      <Lock size={10} />
                    </button>
                    <button
                      className="p-0.5 rounded hover:bg-white/10 text-emerald-300/70 disabled:opacity-50 disabled:cursor-not-allowed"
                      onClick={() => backgroundImageInputRef.current?.click()}
                      title="替换底图"
                      disabled={isBackgroundLocked}
                    >
                      <Upload size={10} />
                    </button>
                    <button
                      className="p-0.5 rounded hover:bg-red-500/20 text-emerald-300/70 hover:text-red-400 disabled:opacity-50 disabled:cursor-not-allowed"
                      onClick={() => updateLayout(draftLayout => { draftLayout.background = { type: 'color', value: '#ffffff' }; })}
                      title="移除底图"
                      disabled={isBackgroundLocked}
                    >
                      <Trash2 size={10} />
                    </button>
                  </div>
                </div>
              );
            }

            const element = layer.element;
            return (
              <div
                key={element.id}
                className={`flex items-center gap-1 px-2 py-1.5 rounded-lg text-xs transition-all cursor-pointer group ${
                  selectedIds.includes(element.id)
                    ? "bg-violet-500/20 text-violet-400"
                    : "text-white/50 hover:bg-white/5 hover:text-white/70"
                }`}
                onClick={(event) => selectElement(element.id, event.shiftKey)}
              >
                <GripVertical size={10} className="text-white/20 shrink-0" />
                <span className="flex-1 truncate">
                  {element.type === 'photo'
                    ? `照片${(element.props as PhotoElementProps).photoNumber}`
                    : element.type === 'text'
                      ? (element.props as TextElementProps).content?.slice(0, 8) || '文本'
                      : element.type === 'shape'
                        ? '形状'
                        : element.type === 'date'
                          ? '日期'
                          : element.type}
                </span>
                <div className="hidden group-hover:flex items-center gap-0.5">
                  <button
                    className="p-0.5 rounded hover:bg-white/10"
                    onClick={(event) => { event.stopPropagation(); moveLayer(element.id, 'up'); }}
                    title="上移"
                  >
                    <ChevronUp size={10} />
                  </button>
                  <button
                    className="p-0.5 rounded hover:bg-white/10"
                    onClick={(event) => { event.stopPropagation(); moveLayer(element.id, 'down'); }}
                    title="下移"
                  >
                    <ChevronDown size={10} />
                  </button>
                  <button
                    className={`p-0.5 rounded hover:bg-white/10 ${element.locked ? 'text-amber-400' : ''}`}
                    onClick={(event) => { event.stopPropagation(); toggleLock(element.id); }}
                    title={element.locked ? '解锁' : '锁定'}
                  >
                    <Lock size={10} />
                  </button>
                  <button
                    className={`p-0.5 rounded hover:bg-white/10 ${!element.visible ? 'text-white/20' : ''}`}
                    onClick={(event) => { event.stopPropagation(); toggleVisibility(element.id); }}
                    title={element.visible ? '隐藏' : '显示'}
                  >
                    <Eye size={10} />
                  </button>
                  <button
                    className="p-0.5 rounded hover:bg-white/10 text-white/40"
                    onClick={(event) => {
                      event.stopPropagation();
                      const draft = JSON.parse(JSON.stringify(undoRedo.present));
                      const originalElement = draft.elements.find((existingElement: TemplateElement) => existingElement.id === element.id);
                      if (originalElement) {
                        const clonedElement = {
                          ...originalElement,
                          id: generateId(),
                          x: originalElement.x + 10,
                          y: originalElement.y + 10,
                          zIndex: Math.max(...draft.elements.map((existingElement: TemplateElement) => existingElement.zIndex)) + 1,
                        };
                        draft.elements.push(clonedElement);
                        undoRedo.set(draft);
                      }
                    }}
                    title="复制"
                  >
                    <Copy size={10} />
                  </button>
                  <button
                    className="p-0.5 rounded hover:bg-red-500/20 text-white/40 hover:text-red-400"
                    onClick={(event) => {
                      event.stopPropagation();
                      const draft = JSON.parse(JSON.stringify(undoRedo.present));
                      draft.elements = draft.elements.filter((existingElement: TemplateElement) => existingElement.id !== element.id);
                      undoRedo.set(draft);
                      setSelectedIds(previousSelectedIds => previousSelectedIds.filter(id => id !== element.id));
                    }}
                    title="删除"
                  >
                    <Trash2 size={10} />
                  </button>
                </div>
              </div>
            );
          })}
          {visibleLayerCount === 0 && (
            <div className="text-[10px] text-white/20 text-center py-4">无元素<br/>从左侧添加</div>
          )}
        </div>

        {/* 属性面板 */}
        <div className="border-t border-white/5 p-3 space-y-3 overflow-y-auto flex-1">
          <div className="text-xs font-semibold text-white/60 uppercase tracking-wider">属性</div>
          {!selectedElement && (
            <div className="text-[10px] text-white/30 text-center py-4">选中元素后<br/>编辑属性</div>
          )}

          {selectedElement && (
            <>
              {/* 通用属性 */}
              <PropertyRow label="X" value={selectedElement.x}
                onChange={v => updateElement(selectedElement.id, { x: Number(v) })} />
              <PropertyRow label="Y" value={selectedElement.y}
                onChange={v => updateElement(selectedElement.id, { y: Number(v) })} />
              <PropertyRow label="W" value={selectedElement.width}
                onChange={v => updateElement(selectedElement.id, { width: Number(v) })} />
              <PropertyRow label="H" value={selectedElement.height}
                onChange={v => updateElement(selectedElement.id, { height: Number(v) })} />
              <PropertyRow label="旋转" value={selectedElement.rotation}
                onChange={v => updateElement(selectedElement.id, { rotation: Number(v) })} />
              <PropertyRow label="透明度" value={selectedElement.opacity} min={0} max={1} step={0.05}
                onChange={v => updateElement(selectedElement.id, { opacity: Number(v) })} />

              {/* 照片框属性 */}
              {selectedElement.type === 'photo' && (
                <>
                  <div className="border-t border-white/5 pt-2">
                    <div className="text-[10px] text-white/40 mb-2">照片框属性</div>
                    <PropertyRow label="照片号" value={(selectedElement.props as PhotoElementProps).photoNumber}
                      onChange={v => updateProp('photoNumber', Number(v))} />
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-[10px] text-white/40">快速切换</span>
                      <div className="flex gap-1">
                        {[1, 2, 3, 4].map(photoNumber => (
                          <button
                            key={photoNumber}
                            className={`px-1.5 py-0.5 rounded text-[10px] ${(selectedElement.props as PhotoElementProps).photoNumber === photoNumber ? 'bg-violet-500/30 text-violet-400' : 'bg-white/5 text-white/40 hover:bg-white/10'}`}
                            onClick={() => updateProp('photoNumber', photoNumber)}
                          >
                            {photoNumber}
                          </button>
                        ))}
                      </div>
                    </div>
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-[10px] text-white/40">裁剪</span>
                      <div className="flex gap-1">
                        {(
                          [
                            { v: 'fill', l: '填充' },
                            { v: 'fit', l: '适应' },
                            { v: 'stretch', l: '拉伸' },
                          ] as { v: PhotoElementProps['cropMode']; l: string }[]
                        ).map(opt => (
                          <button
                            key={opt.v}
                            className={`px-1.5 py-0.5 rounded text-[10px] ${(selectedElement.props as PhotoElementProps).cropMode === opt.v ? 'bg-violet-500/30 text-violet-400' : 'bg-white/5 text-white/40 hover:bg-white/10'}`}
                            onClick={() => updateProp('cropMode', opt.v)}
                          >
                            {opt.l}
                          </button>
                        ))}
                      </div>
                    </div>
                    <PropertyRow label="圆角" value={(selectedElement.props as PhotoElementProps).borderRadius}
                      onChange={v => updateProp('borderRadius', Number(v))} />
                  </div>
                </>
              )}

              {/* 文本属性 */}
              {selectedElement.type === 'text' && (
                <>
                  <div className="border-t border-white/5 pt-2">
                    <div className="text-[10px] text-white/40 mb-2">文本属性</div>
                    <div className="space-y-1 mb-2">
                      <textarea
                        className="w-full bg-white/5 border border-white/10 rounded px-2 py-1 text-[10px] text-white/80 outline-none resize-none"
                        rows={2}
                        value={(selectedElement.props as TextElementProps).content}
                        onChange={e => updateProp('content', e.target.value)}
                      />
                    </div>
                    <PropertyRow label="字体" value={(selectedElement.props as TextElementProps).fontFamily} string
                      onChange={v => updateProp('fontFamily', v)} />
                    <PropertyRow label="字号" value={(selectedElement.props as TextElementProps).fontSize}
                      onChange={v => updateProp('fontSize', Number(v))} />
                    <PropertyRow label="颜色"
                      display={<input type="color" className="w-5 h-5 rounded cursor-pointer border-0 p-0 bg-transparent"
                        value={(selectedElement.props as TextElementProps).color}
                        onChange={e => updateProp('color', e.target.value)} />}
                    />
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-[10px] text-white/40">对齐</span>
                      <div className="flex gap-1">
                        {(['left', 'center', 'right'] as TextElementProps['textAlign'][]).map(a => (
                          <button
                            key={a}
                            className={`px-1.5 py-0.5 rounded text-[10px] ${(selectedElement.props as TextElementProps).textAlign === a ? 'bg-violet-500/30 text-violet-400' : 'bg-white/5 text-white/40 hover:bg-white/10'}`}
                            onClick={() => updateProp('textAlign', a)}
                          >
                            {a === 'left' ? '左' : a === 'center' ? '中' : '右'}
                          </button>
                        ))}
                      </div>
                    </div>
                  </div>
                </>
              )}

              {/* 形状属性 */}
              {selectedElement.type === 'shape' && (
                <>
                  <div className="border-t border-white/5 pt-2">
                    <div className="text-[10px] text-white/40 mb-2">形状属性</div>
                    <PropertyRow label="填充色"
                      display={<input type="color" className="w-5 h-5 rounded cursor-pointer border-0 p-0 bg-transparent"
                        value={(selectedElement.props as ShapeElementProps).fillColor}
                        onChange={e => updateProp('fillColor', e.target.value)} />}
                    />
                    <PropertyRow label="描边色"
                      display={<input type="color" className="w-5 h-5 rounded cursor-pointer border-0 p-0 bg-transparent"
                        value={(selectedElement.props as ShapeElementProps).strokeColor}
                        onChange={e => updateProp('strokeColor', e.target.value)} />}
                    />
                    <PropertyRow label="描边宽" value={(selectedElement.props as ShapeElementProps).strokeWidth}
                      onChange={v => updateProp('strokeWidth', Number(v))} />
                    <PropertyRow label="圆角" value={(selectedElement.props as ShapeElementProps).borderRadius}
                      onChange={v => updateProp('borderRadius', Number(v))} />
                  </div>
                </>
              )}

              {/* 图片属性 */}
              {selectedElement.type === 'image' && (
                <>
                  <div className="border-t border-white/5 pt-2">
                    <div className="text-[10px] text-white/40 mb-2">图片属性</div>
                    <input
                      ref={elementImageInputRef}
                      type="file"
                      accept="image/png,image/jpeg,image/webp,image/gif"
                      className="hidden"
                      onChange={event => {
                        const file = event.target.files?.[0];
                        if (file) void importSelectedImageElement(file);
                      }}
                    />
                    <button
                      className="w-full flex items-center justify-center gap-2 px-2 py-1.5 rounded bg-emerald-500/10 hover:bg-emerald-500/20 text-[10px] text-emerald-300 transition-colors mb-2"
                      onClick={() => elementImageInputRef.current?.click()}
                    >
                      <Upload size={12} />
                      上传图片
                    </button>
                    <PropertyRow label="说明" value={(selectedElement.props as ImageElementProps).alt || ''} string
                      onChange={v => updateProp('alt', v)} />
                  </div>
                </>
              )}

              {/* 日期属性 */}
              {(selectedElement.type === 'date' || selectedElement.type === 'datetime') && (
                <>
                  <div className="border-t border-white/5 pt-2">
                    <div className="text-[10px] text-white/40 mb-2">日期属性</div>
                    <div className="space-y-1">
                      {['YYYY-MM-DD', 'MM/DD/YYYY', 'DD.MM.YYYY', 'YYYY年MM月DD日', 'YYYY-MM-DD HH:mm'].map(fmt => (
                        <button
                          key={fmt}
                          className={`w-full px-2 py-1 rounded text-[10px] text-left ${(selectedElement.props as DateElementProps).format === fmt ? 'bg-violet-500/30 text-violet-400' : 'bg-white/5 text-white/40 hover:bg-white/10'}`}
                          onClick={() => updateProp('format', fmt)}
                        >
                          {fmt}
                        </button>
                      ))}
                    </div>
                  </div>
                </>
              )}

              {/* 二维码属性 */}
              {selectedElement.type === 'qr_code' && (
                <>
                  <div className="border-t border-white/5 pt-2">
                    <div className="text-[10px] text-white/40 mb-2">二维码属性</div>
                    <div className="space-y-1 mb-2">
                      <input
                        className="w-full bg-white/5 border border-white/10 rounded px-2 py-1 text-[10px] text-white/80 outline-none"
                        value={(selectedElement.props as QrCodeElementProps).url}
                        onChange={e => updateProp('url', e.target.value)}
                        placeholder="输入URL"
                      />
                    </div>
                  </div>
                </>
              )}
            </>
          )}
        </div>
      </GlassCard>
    </div>
  );
}

// ─── 属性行组件 ───
function PropertyRow({
  label,
  value,
  onChange,
  min,
  max,
  step,
  string,
  display,
}: {
  label: string;
  value?: string | number;
  onChange?: (v: string) => void;
  min?: number;
  max?: number;
  step?: number;
  string?: boolean;
  display?: React.ReactNode;
}) {
  return (
    <div className="flex items-center justify-between mb-1">
      <span className="text-[10px] text-white/40">{label}</span>
      {display || (
        string ? (
          <input
            className="bg-white/5 border border-white/10 rounded px-1.5 py-0.5 text-[10px] text-white/70 font-mono w-16 text-center outline-none"
            value={value as string}
            onChange={e => onChange?.(e.target.value)}
          />
        ) : (
          <input
            type="number"
            className="bg-white/5 border border-white/10 rounded px-1.5 py-0.5 text-[10px] text-white/70 font-mono w-16 text-center outline-none"
            value={value as number}
            min={min}
            max={max}
            step={step ?? 1}
            onChange={e => onChange?.(e.target.value)}
          />
        )
      )}
    </div>
  );
}
