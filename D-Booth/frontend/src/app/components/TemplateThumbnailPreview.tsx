import type React from "react";
import type {
  DateElementProps,
  ImageElementProps,
  PhotoElementProps,
  ShapeElementProps,
  TemplateElement,
  TemplateLayout,
  TextElementProps,
} from "../types/template";

function getCanvasSize(layout: TemplateLayout) {
  return {
    width: Math.max(1, Math.round(layout.paperSize.width * layout.resolution / 25.4)),
    height: Math.max(1, Math.round(layout.paperSize.height * layout.resolution / 25.4)),
  };
}

function isBrowserRenderableImage(src: string) {
  return /^(https?:|blob:|data:|\/)/i.test(src);
}

function getElementStyle(element: TemplateElement, canvas: { width: number; height: number }): React.CSSProperties {
  return {
    position: "absolute",
    left: `${element.x / canvas.width * 100}%`,
    top: `${element.y / canvas.height * 100}%`,
    width: `${element.width / canvas.width * 100}%`,
    height: `${element.height / canvas.height * 100}%`,
    opacity: element.opacity,
    zIndex: element.zIndex,
    transform: `rotate(${element.rotation}deg)`,
    transformOrigin: "center",
    overflow: "hidden",
  };
}

function renderThumbnailElement(element: TemplateElement, canvas: { width: number; height: number }) {
  if (!element.visible) return null;

  const baseStyle = getElementStyle(element, canvas);

  if (element.type === "photo") {
    const props = element.props as PhotoElementProps;
    return (
      <div
        key={element.id}
        className="grid place-items-center border border-slate-900/20 bg-slate-900/10 text-[clamp(5px,7cqi,12px)] font-semibold text-slate-900/45"
        style={{ ...baseStyle, borderRadius: props.borderRadius }}
      >
        {props.photoNumber}
      </div>
    );
  }

  if (element.type === "text") {
    const props = element.props as TextElementProps;
    return (
      <div
        key={element.id}
        style={{
          ...baseStyle,
          color: props.color,
          fontFamily: props.fontFamily,
          fontSize: `clamp(4px, ${props.fontSize / canvas.width * 100}cqi, 13px)`,
          fontWeight: props.fontWeight,
          lineHeight: props.lineHeight,
          textAlign: props.textAlign,
          display: "flex",
          alignItems: "center",
          justifyContent: props.textAlign === "left" ? "flex-start" : props.textAlign === "right" ? "flex-end" : "center",
          padding: "0 2%",
          whiteSpace: "pre-wrap",
        }}
      >
        {props.content}
      </div>
    );
  }

  if (element.type === "shape") {
    const props = element.props as ShapeElementProps;
    const isEllipse = props.shapeType === "ellipse";
    return (
      <div
        key={element.id}
        style={{
          ...baseStyle,
          background: props.fillColor,
          border: `${Math.max(1, props.strokeWidth / 6)}px solid ${props.strokeColor}`,
          borderRadius: isEllipse ? "9999px" : Math.max(0, props.borderRadius / 6),
        }}
      />
    );
  }

  if (element.type === "image") {
    const props = element.props as ImageElementProps;
    const canRender = props.src && isBrowserRenderableImage(props.src);
    return (
      <div key={element.id} className="bg-white/40" style={baseStyle}>
        {canRender ? (
          <img src={props.src} alt={props.alt} className="h-full w-full object-cover" draggable={false} />
        ) : (
          <div className="grid h-full w-full place-items-center text-[clamp(5px,6cqi,10px)] text-slate-900/35">素材</div>
        )}
      </div>
    );
  }

  if (element.type === "date" || element.type === "datetime") {
    const props = element.props as DateElementProps;
    const value = props.format.includes("YYYY") ? "2026/07/04" : "2026/07/04 18:00";
    return (
      <div key={element.id} className="grid place-items-center text-[clamp(4px,4cqi,10px)] font-medium text-slate-700" style={baseStyle}>
        {value}
      </div>
    );
  }

  if (element.type === "qr_code") {
    return (
      <div key={element.id} className="grid place-items-center border border-slate-900 bg-white text-[clamp(4px,5cqi,10px)] font-semibold text-slate-500" style={baseStyle}>
        QR
      </div>
    );
  }

  return null;
}

export function TemplateThumbnailPreview({ layout }: { layout: TemplateLayout | null }) {
  if (!layout) {
    return (
      <div className="grid h-full w-full place-items-center bg-white text-[10px] font-medium text-slate-400">
        需要保存版式
      </div>
    );
  }

  const canvas = getCanvasSize(layout);
  const backgroundStyle: React.CSSProperties =
    layout.background.type === "image"
      ? { backgroundImage: `url(${layout.background.value})`, backgroundSize: "cover", backgroundPosition: "center" }
      : { background: layout.background.value };

  return (
    <div className="flex h-full w-full items-center justify-center bg-slate-950/20 p-1">
      <div
        className="relative max-h-full max-w-full overflow-hidden bg-white shadow-sm"
        style={{
          aspectRatio: `${canvas.width} / ${canvas.height}`,
          height: canvas.height >= canvas.width ? "100%" : "auto",
          width: canvas.width > canvas.height ? "100%" : "auto",
          containerType: "inline-size",
          ...backgroundStyle,
        }}
      >
        {[...layout.elements].sort((a, b) => a.zIndex - b.zIndex).map(element => renderThumbnailElement(element, canvas))}
      </div>
    </div>
  );
}
