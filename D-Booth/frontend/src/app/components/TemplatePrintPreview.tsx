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

function getObjectFit(cropMode: PhotoElementProps["cropMode"]) {
  if (cropMode === "fit") return "contain";
  if (cropMode === "stretch") return "fill";
  return "cover";
}

function isBrowserRenderableImage(src: string) {
  return /^(https?:|blob:|data:|\/)/i.test(src);
}

function renderElement(element: TemplateElement, photoUrls: string[]) {
  if (!element.visible) return null;

  const baseStyle: React.CSSProperties = {
    position: "absolute",
    left: `${element.x}px`,
    top: `${element.y}px`,
    width: `${element.width}px`,
    height: `${element.height}px`,
    opacity: element.opacity,
    zIndex: element.zIndex,
    transform: `rotate(${element.rotation}deg)`,
    transformOrigin: "center",
    overflow: "hidden",
  };

  if (element.type === "photo") {
    const props = element.props as PhotoElementProps;
    const photoUrl = photoUrls[props.photoNumber - 1];

    return (
      <div
        key={element.id}
        style={{ ...baseStyle, borderRadius: props.borderRadius }}
        className="bg-neutral-200"
      >
        {photoUrl ? (
          <img
            src={photoUrl}
            alt={`photo ${props.photoNumber}`}
            className="h-full w-full"
            style={{ objectFit: getObjectFit(props.cropMode) }}
            draggable={false}
          />
        ) : (
          <div className="flex h-full w-full items-center justify-center text-[52px] font-semibold text-neutral-400">
            PHOTO {props.photoNumber}
          </div>
        )}
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
          fontSize: props.fontSize,
          fontWeight: props.fontWeight,
          lineHeight: props.lineHeight,
          textAlign: props.textAlign,
          display: "flex",
          alignItems: "center",
          justifyContent: props.textAlign === "left" ? "flex-start" : props.textAlign === "right" ? "flex-end" : "center",
          padding: "0 8px",
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
          border: `${props.strokeWidth}px solid ${props.strokeColor}`,
          borderRadius: isEllipse ? "9999px" : props.borderRadius,
        }}
      />
    );
  }

  if (element.type === "image") {
    const props = element.props as ImageElementProps;
    const canRender = props.src && isBrowserRenderableImage(props.src);
    return (
      <div key={element.id} style={baseStyle} className="bg-neutral-100">
        {canRender ? (
          <img src={props.src} alt={props.alt} className="h-full w-full object-cover" draggable={false} />
        ) : (
          <div className="flex h-full w-full items-center justify-center px-3 text-center text-[42px] font-semibold text-neutral-400">
            素材需替换
          </div>
        )}
      </div>
    );
  }

  if (element.type === "date" || element.type === "datetime") {
    const props = element.props as DateElementProps;
    const value = props.format.includes("YYYY") ? new Date().toLocaleDateString("zh-CN") : new Date().toLocaleString("zh-CN");
    return (
      <div
        key={element.id}
        style={baseStyle}
        className="flex items-center justify-center text-[48px] font-medium text-neutral-700"
      >
        {value}
      </div>
    );
  }

  if (element.type === "qr_code") {
    return (
      <div
        key={element.id}
        style={baseStyle}
        className="grid place-items-center border-8 border-neutral-900 bg-white text-[42px] font-semibold text-neutral-500"
      >
        QR
      </div>
    );
  }

  return null;
}

export function TemplatePrintPreview({
  layout,
  photoUrls,
  className = "",
}: {
  layout: TemplateLayout;
  photoUrls: string[];
  className?: string;
}) {
  const canvas = getCanvasSize(layout);
  const backgroundStyle: React.CSSProperties =
    layout.background.type === "image"
      ? { backgroundImage: `url(${layout.background.value})`, backgroundSize: "cover", backgroundPosition: "center" }
      : { background: layout.background.value };

  return (
    <div className={`h-full w-full overflow-hidden bg-white ${className}`}>
      <div
        className="relative origin-top-left"
        style={{
          width: canvas.width,
          height: canvas.height,
          transform: `scale(var(--template-preview-scale, 1))`,
          ...backgroundStyle,
        }}
      >
        {[...layout.elements].sort((a, b) => a.zIndex - b.zIndex).map(element => renderElement(element, photoUrls))}
      </div>
    </div>
  );
}

export function getTemplateCanvasSize(layout: TemplateLayout) {
  return getCanvasSize(layout);
}
