import { useState, useRef, useEffect } from "react";
import { Trash2 } from "lucide-react";

export interface Sticker {
  id: string;
  propId: string;
  imageUrl: string;
  x: number; // 0-1比例
  y: number; // 0-1比例
  scale: number; // 0.1-3.0
  rotation: number; // 0-360
  flipH: boolean;
  flipV: boolean;
  opacity: number; // 0-1
}

interface StickerOverlayProps {
  photoUrl: string;
  stickers: Sticker[];
  onChange: (stickers: Sticker[]) => void;
  onStickerSelect?: (stickerId: string | null) => void;
  selectedStickerId: string | null;
}

function isImageStickerSource(src: string): boolean {
  return /^(blob:|data:|https?:\/\/|\/)/i.test(src);
}

function StickerVisual({ sticker }: { sticker: Sticker }) {
  if (isImageStickerSource(sticker.imageUrl)) {
    return (
      <img
        src={sticker.imageUrl}
        alt="Sticker"
        className="w-16 h-16 object-contain pointer-events-none"
        draggable={false}
      />
    );
  }

  return (
    <span className="flex h-16 w-16 items-center justify-center text-5xl leading-none pointer-events-none">
      {sticker.imageUrl}
    </span>
  );
}

export function StickerOverlay({
  photoUrl,
  stickers,
  onChange,
  onStickerSelect,
  selectedStickerId
}: StickerOverlayProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [isResizing, setIsResizing] = useState(false);
  const [isRotating, setIsRotating] = useState(false);
  const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 });
  const [startScale, setStartScale] = useState(1);
  const [startRotation, setStartRotation] = useState(0);
  const [startPointerPos, setStartPointerPos] = useState({ x: 0, y: 0 });

  const handleStickerClick = (e: React.MouseEvent, stickerId: string) => {
    e.stopPropagation();
    onStickerSelect?.(stickerId);
  };

  const handleContainerClick = () => {
    onStickerSelect?.(null);
  };

  const handleDeleteSticker = (e: React.MouseEvent, stickerId: string) => {
    e.stopPropagation();
    onChange(stickers.filter(s => s.id !== stickerId));
    onStickerSelect?.(null);
  };

  const handleMouseDown = (e: React.MouseEvent, stickerId: string) => {
    if (e.button !== 0) return; // Only left click
    e.stopPropagation();

    const sticker = stickers.find(s => s.id === stickerId);
    if (!sticker) return;

    onStickerSelect?.(stickerId);
    setIsDragging(true);

    const rect = containerRef.current?.getBoundingClientRect();
    if (!rect) return;

    const mouseX = e.clientX - rect.left;
    const mouseY = e.clientY - rect.top;
    const stickerX = sticker.x * rect.width;
    const stickerY = sticker.y * rect.height;

    setDragOffset({
      x: mouseX - stickerX,
      y: mouseY - stickerY
    });
  };

  const handleResizeStart = (e: React.MouseEvent, stickerId: string) => {
    e.stopPropagation();
    const sticker = stickers.find(s => s.id === stickerId);
    if (!sticker) return;

    setIsResizing(true);
    setStartScale(sticker.scale);
    setStartPointerPos({ x: e.clientX, y: e.clientY });
  };

  const handleRotateStart = (e: React.MouseEvent, stickerId: string) => {
    e.stopPropagation();
    const sticker = stickers.find(s => s.id === stickerId);
    if (!sticker) return;

    setIsRotating(true);
    setStartRotation(sticker.rotation);
    setStartPointerPos({ x: e.clientX, y: e.clientY });
  };

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!containerRef.current) return;
      const rect = containerRef.current.getBoundingClientRect();

      if (isDragging && selectedStickerId) {
        const mouseX = e.clientX - rect.left;
        const mouseY = e.clientY - rect.top;

        const newX = (mouseX - dragOffset.x) / rect.width;
        const newY = (mouseY - dragOffset.y) / rect.height;

        // Clamp to 0-1 range
        const clampedX = Math.max(0, Math.min(1, newX));
        const clampedY = Math.max(0, Math.min(1, newY));

        onChange(stickers.map(s =>
          s.id === selectedStickerId
            ? { ...s, x: clampedX, y: clampedY }
            : s
        ));
      }

      if (isResizing && selectedStickerId) {
        const deltaX = e.clientX - startPointerPos.x;
        const deltaY = e.clientY - startPointerPos.y;
        const delta = Math.sqrt(deltaX * deltaX + deltaY * deltaY) * (deltaX > 0 ? 1 : -1);
        const newScale = Math.max(0.1, Math.min(3.0, startScale + delta / 100));

        onChange(stickers.map(s =>
          s.id === selectedStickerId
            ? { ...s, scale: newScale }
            : s
        ));
      }

      if (isRotating && selectedStickerId) {
        const deltaX = e.clientX - startPointerPos.x;
        const newRotation = (startRotation + deltaX / 2) % 360;
        const normalizedRotation = newRotation < 0 ? newRotation + 360 : newRotation;

        onChange(stickers.map(s =>
          s.id === selectedStickerId
            ? { ...s, rotation: normalizedRotation }
            : s
        ));
      }
    };

    const handleMouseUp = () => {
      setIsDragging(false);
      setIsResizing(false);
      setIsRotating(false);
    };

    if (isDragging || isResizing || isRotating) {
      window.addEventListener('mousemove', handleMouseMove);
      window.addEventListener('mouseup', handleMouseUp);
    }

    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isDragging, isResizing, isRotating, selectedStickerId, stickers, onChange, dragOffset, startScale, startRotation, startPointerPos]);

  return (
    <div
      ref={containerRef}
      className="relative w-full h-full"
      onClick={handleContainerClick}
    >
      <img
        src={photoUrl}
        alt="Photo"
        className="w-full h-full object-cover"
        draggable={false}
      />

      {stickers.map(sticker => {
        const isSelected = selectedStickerId === sticker.id;
        return (
          <div
            key={sticker.id}
            className={`absolute select-none transition-shadow ${isSelected ? 'z-10' : 'z-0'}`}
            style={{
              left: `${sticker.x * 100}%`,
              top: `${sticker.y * 100}%`,
              transform: `translate(-50%, -50%) scale(${sticker.scale}) rotate(${sticker.rotation}deg) ${sticker.flipH ? 'scaleX(-1)' : ''} ${sticker.flipV ? 'scaleY(-1)' : ''}`,
              opacity: sticker.opacity,
              cursor: isDragging && isSelected ? 'grabbing' : 'grab',
            }}
            onClick={(e) => handleStickerClick(e, sticker.id)}
            onMouseDown={(e) => handleMouseDown(e, sticker.id)}
          >
            <StickerVisual sticker={sticker} />

            {isSelected && (
              <>
                {/* Selection border */}
                <div className="absolute inset-0 border-2 border-blue-500 rounded pointer-events-none" />

                {/* Delete button */}
                <button
                  className="absolute -top-2 -right-2 w-5 h-5 bg-red-500 rounded-full flex items-center justify-center text-white hover:bg-red-600"
                  onClick={(e) => handleDeleteSticker(e, sticker.id)}
                >
                  <Trash2 size={10} />
                </button>

                {/* Resize handle */}
                <div
                  className="absolute -bottom-2 -right-2 w-5 h-5 bg-blue-500 rounded-full cursor-nwse-resize flex items-center justify-center text-white"
                  onMouseDown={(e) => handleResizeStart(e, sticker.id)}
                >
                  <svg width={10} height={10} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
                    <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z" />
                  </svg>
                </div>

                {/* Rotate handle */}
                <div
                  className="absolute -bottom-2 -left-2 w-5 h-5 bg-green-500 rounded-full cursor-pointer flex items-center justify-center text-white"
                  onMouseDown={(e) => handleRotateStart(e, sticker.id)}
                >
                  <svg width={10} height={10} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
                    <path d="M21.5 2v6h-6M2.5 22v-6h6M2 11.5a10 10 0 0 1 18.8-4.3M22 12.5a10 10 0 0 1-18.8 4.2" />
                  </svg>
                </div>
              </>
            )}
          </div>
        );
      })}
    </div>
  );
}
