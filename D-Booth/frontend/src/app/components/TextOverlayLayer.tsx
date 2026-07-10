import { useRef } from "react";

export interface TextOverlay {
  id: string;
  text: string;
  x: number;
  y: number;
  size: number;
  color: string;
  rotation: number;
  opacity: number;
}

interface TextOverlayLayerProps {
  texts: TextOverlay[];
  selectedTextId: string | null;
  interactive?: boolean;
  onChange: (texts: TextOverlay[]) => void;
  onSelect: (textId: string | null) => void;
}

export function TextOverlayLayer({
  texts,
  selectedTextId,
  interactive = true,
  onChange,
  onSelect,
}: TextOverlayLayerProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const draggingTextIdRef = useRef<string | null>(null);

  const updatePosition = (clientX: number, clientY: number) => {
    const textId = draggingTextIdRef.current;
    const rect = containerRef.current?.getBoundingClientRect();
    if (!textId || !rect) return;

    const x = Math.max(0, Math.min(1, (clientX - rect.left) / rect.width));
    const y = Math.max(0, Math.min(1, (clientY - rect.top) / rect.height));
    onChange(texts.map(item => item.id === textId ? { ...item, x, y } : item));
  };

  return (
    <div
      ref={containerRef}
      className={`absolute inset-0 z-20 ${interactive ? "" : "pointer-events-none"}`}
      style={{ containerType: "size" }}
      onPointerMove={event => updatePosition(event.clientX, event.clientY)}
      onPointerUp={event => {
        draggingTextIdRef.current = null;
        if (event.currentTarget.hasPointerCapture(event.pointerId)) {
          event.currentTarget.releasePointerCapture(event.pointerId);
        }
      }}
      onPointerCancel={() => {
        draggingTextIdRef.current = null;
      }}
      onPointerDown={() => onSelect(null)}
    >
      {texts.map(item => {
        const isSelected = item.id === selectedTextId;
        return (
          <button
            key={item.id}
            type="button"
            className={`absolute max-w-[90%] cursor-move touch-none whitespace-nowrap border px-1 py-0.5 font-bold leading-tight ${
              isSelected && interactive
                ? "border-violet-400 bg-black/20"
                : "border-transparent bg-transparent"
            }`}
            style={{
              left: `${item.x * 100}%`,
              top: `${item.y * 100}%`,
              color: item.color,
              fontSize: `${item.size}cqh`,
              opacity: item.opacity,
              textShadow: "0 2px 6px rgba(0, 0, 0, 0.75)",
              transform: `translate(-50%, -50%) rotate(${item.rotation}deg)`,
            }}
            onPointerDown={event => {
              if (!interactive) return;
              event.stopPropagation();
              draggingTextIdRef.current = item.id;
              onSelect(item.id);
              containerRef.current?.setPointerCapture(event.pointerId);
            }}
          >
            {item.text}
          </button>
        );
      })}
    </div>
  );
}
