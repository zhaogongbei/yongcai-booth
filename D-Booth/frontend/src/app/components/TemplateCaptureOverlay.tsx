import type { PhotoElementProps, TemplateElement, TemplateLayout } from "../types/template";

function getTemplateCanvasSize(layout: TemplateLayout) {
  return {
    width: Math.max(1, Math.round(layout.paperSize.width * layout.resolution / 25.4)),
    height: Math.max(1, Math.round(layout.paperSize.height * layout.resolution / 25.4)),
  };
}

function getVisiblePhotoElements(layout: TemplateLayout): TemplateElement[] {
  return [...layout.elements]
    .filter(element => element.visible && element.type === "photo")
    .sort((leftElement, rightElement) => leftElement.zIndex - rightElement.zIndex);
}

export function TemplateCaptureOverlay({
  layout,
  capturedPhotoCount,
}: {
  layout: TemplateLayout;
  capturedPhotoCount: number;
}) {
  const canvas = getTemplateCanvasSize(layout);
  const photoElements = getVisiblePhotoElements(layout);

  if (photoElements.length === 0) {
    return null;
  }

  return (
    <div className="pointer-events-none absolute inset-0 z-10">
      <svg
        className="h-full w-full"
        viewBox={`0 0 ${canvas.width} ${canvas.height}`}
        preserveAspectRatio="xMidYMid meet"
        aria-hidden="true"
      >
        {photoElements.map(photoElement => {
          const photoProps = photoElement.props as PhotoElementProps;
          const isCaptured = capturedPhotoCount >= photoProps.photoNumber;
          const strokeColor = isCaptured ? "rgba(52, 211, 153, 0.95)" : "rgba(56, 189, 248, 0.95)";
          const fillColor = isCaptured ? "rgba(16, 185, 129, 0.12)" : "rgba(56, 189, 248, 0.12)";
          const labelBackgroundColor = isCaptured ? "rgba(5, 150, 105, 0.92)" : "rgba(15, 23, 42, 0.88)";
          const labelText = `照片 ${photoProps.photoNumber}`;

          return (
            <g key={photoElement.id}>
              <rect
                x={photoElement.x}
                y={photoElement.y}
                width={photoElement.width}
                height={photoElement.height}
                rx={Math.max(0, photoProps.borderRadius || 0)}
                ry={Math.max(0, photoProps.borderRadius || 0)}
                fill={fillColor}
                stroke={strokeColor}
                strokeWidth={8}
                strokeDasharray="22 12"
              />
              <rect
                x={photoElement.x + 16}
                y={photoElement.y + 16}
                width={Math.max(120, labelText.length * 24)}
                height={44}
                rx={22}
                ry={22}
                fill={labelBackgroundColor}
              />
              <text
                x={photoElement.x + 36}
                y={photoElement.y + 45}
                fill="white"
                fontSize={24}
                fontWeight={700}
              >
                {labelText}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}
