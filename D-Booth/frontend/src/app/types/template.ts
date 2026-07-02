export interface PhotoElementProps {
  photoNumber: number; // 1-4
  cropMode: 'fill' | 'fit' | 'stretch';
  borderRadius: number;
}

export interface TextElementProps {
  content: string;
  fontFamily: string;
  fontSize: number;
  fontWeight: number;
  color: string;
  textAlign: 'left' | 'center' | 'right';
  lineHeight: number;
}

export interface ShapeElementProps {
  shapeType: 'rectangle' | 'ellipse' | 'line' | 'star';
  fillColor: string;
  strokeColor: string;
  strokeWidth: number;
  borderRadius: number;
}

export interface ImageElementProps {
  src: string;
  alt: string;
}

export interface QrCodeElementProps {
  url: string;
}

export interface DateElementProps {
  format: string; // YYYY-MM-DD, MM/DD/YYYY, etc.
}

export type ElementProps =
  | PhotoElementProps
  | TextElementProps
  | ShapeElementProps
  | ImageElementProps
  | QrCodeElementProps
  | DateElementProps;

export interface TemplateElement {
  id: string;
  type: 'photo' | 'text' | 'shape' | 'image' | 'qr_code' | 'date' | 'datetime' | 'filename' | 'survey_answer' | 'session_number' | 'signature';
  x: number;     // 位置(像素)
  y: number;
  width: number;  // 尺寸(像素)
  height: number;
  rotation: number; // 旋转角度 0-360
  opacity: number;  // 透明度 0-1
  zIndex: number;   // 图层顺序
  locked: boolean;  // 是否锁定
  visible: boolean; // 是否可见
  // 类型特有属性
  props: ElementProps;
}

export interface TemplateLayout {
  id: string;
  name: string;
  paperSize: { width: number; height: number }; // 毫米
  resolution: number;   // DPI (300)
  orientation: 'portrait' | 'landscape';
  background: { type: 'color' | 'gradient' | 'image'; value: string };
  elements: TemplateElement[];
}

export interface TemplatePreset {
  id: string;
  name: string;
  description: string;
  thumbnail: string;
  layout: Omit<TemplateLayout, 'id' | 'name'>;
}