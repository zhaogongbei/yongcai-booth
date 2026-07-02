import { useRef, useEffect, useState, useCallback } from 'react';
import ProgressiveImage from './ProgressiveImage';

interface PhotoItem {
  id: string;
  original_url: string;
  thumbnail_url: string;
  thumbnail_urls: Record<string, string>;
  webp_url?: string;
  width: number;
  height: number;
}

interface VirtualPhotoGridProps {
  photos: PhotoItem[];
  columnCount?: number;
  gap?: number;
  onPhotoClick?: (photo: PhotoItem) => void;
  overscan?: number;
  loadMore?: () => void;
  hasMore?: boolean;
}

interface RenderedItem {
  index: number;
  top: number;
  height: number;
}

const VirtualPhotoGrid = ({
  photos,
  columnCount = 3,
  gap = 8,
  onPhotoClick,
  overscan = 5,
  loadMore,
  hasMore = false,
}: VirtualPhotoGridProps) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [containerWidth, setContainerWidth] = useState(0);
  const [scrollTop, setScrollTop] = useState(0);
  const [containerHeight, setContainerHeight] = useState(0);
  const [estimatedHeights, setEstimatedHeights] = useState<Record<number, number>>({});

  // Calculate item width based on container and columns
  const itemWidth = containerWidth > 0
    ? (containerWidth - gap * (columnCount - 1)) / columnCount
    : 100;

  // Calculate item positions
  const getItemLayout = useCallback(() => {
    const rowCount = Math.ceil(photos.length / columnCount);
    const layouts: Array<{ index: number; top: number; height: number; col: number; row: number }> = [];

    for (let i = 0; i < photos.length; i++) {
      const row = Math.floor(i / columnCount);
      const col = i % columnCount;

      // Estimate height based on aspect ratio
      let itemHeight = itemWidth; // Default square

      const photo = photos[i];
      if (photo.width && photo.height) {
        itemHeight = itemWidth * (photo.height / photo.width);
      }

      // Use measured height if available
      const measuredHeight = estimatedHeights[i];
      if (measuredHeight) {
        itemHeight = measuredHeight;
      }

      // Calculate top by summing heights of previous rows
      let top = 0;
      for (let r = 0; r < row; r++) {
        const rowStartIdx = r * columnCount;
        let maxRowHeight = itemWidth;
        for (let c = 0; c < columnCount; c++) {
          const idx = rowStartIdx + c;
          if (idx < photos.length) {
            const measured = estimatedHeights[idx] || itemWidth;
            const photoAtIdx = photos[idx];
            if (photoAtIdx && photoAtIdx.width && photoAtIdx.height) {
              const estimated = itemWidth * (photoAtIdx.height / photoAtIdx.width);
              maxRowHeight = Math.max(maxRowHeight, measured || estimated);
            } else {
              maxRowHeight = Math.max(maxRowHeight, measured);
            }
          }
        }
        top += maxRowHeight + gap;
      }

      layouts.push({ index: i, top, height: itemHeight, col, row });
    }

    return layouts;
  }, [photos, columnCount, itemWidth, gap, estimatedHeights]);

  // Calculate total height
  const getTotalHeight = useCallback(() => {
    const rowCount = Math.ceil(photos.length / columnCount);
    let totalHeight = 0;

    for (let r = 0; r < rowCount; r++) {
      let maxRowHeight = itemWidth;
      for (let c = 0; c < columnCount; c++) {
        const idx = r * columnCount + c;
        if (idx < photos.length) {
          const measured = estimatedHeights[idx];
          const photo = photos[idx];
          if (photo.width && photo.height) {
            maxRowHeight = Math.max(maxRowHeight, measured || itemWidth * (photo.height / photo.width));
          } else {
            maxRowHeight = Math.max(maxRowHeight, measured || itemWidth);
          }
        }
      }
      totalHeight += maxRowHeight + gap;
    }
    return totalHeight > 0 ? totalHeight - gap : 0;
  }, [photos.length, columnCount, itemWidth, gap, estimatedHeights]);

  // Calculate visible items
  const getVisibleItems = useCallback((): RenderedItem[] => {
    const layouts = getItemLayout();
    const startY = scrollTop - overscan * itemWidth;
    const endY = scrollTop + containerHeight + overscan * itemWidth;

    // Binary search for start
    let startIdx = 0;
    let lo = 0;
    let hi = layouts.length - 1;
    while (lo <= hi) {
      const mid = Math.floor((lo + hi) / 2);
      if (layouts[mid].top < startY) {
        lo = mid + 1;
      } else {
        startIdx = mid;
        hi = mid - 1;
      }
    }

    const visible: RenderedItem[] = [];
    for (let i = startIdx; i < layouts.length; i++) {
      const item = layouts[i];
      if (item.top > endY) break;
      visible.push({ index: item.index, top: item.top, height: item.height });
    }

    return visible;
  }, [getItemLayout, scrollTop, containerHeight, itemWidth, overscan]);

  // Handle scroll
  const handleScroll = useCallback(() => {
    const container = containerRef.current;
    if (!container) return;
    setScrollTop(container.scrollTop);
    setContainerHeight(container.clientHeight);

    // Trigger load more when near bottom
    if (loadMore && hasMore) {
      const scrollBottom = container.scrollTop + container.clientHeight;
      const totalHeight = getTotalHeight();
      if (scrollBottom >= totalHeight - 200) {
        loadMore();
      }
    }
  }, [loadMore, hasMore, getTotalHeight]);

  // Handle image load to measure actual height
  const handleImageLoad = (index: number) => (e: React.SyntheticEvent<HTMLImageElement>) => {
    const img = e.currentTarget;
    setEstimatedHeights(prev => ({
      ...prev,
      [index]: img.offsetHeight,
    }));
  };

  // Resize observer for container
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const resizeObserver = new ResizeObserver((entries) => {
      for (const entry of entries) {
        setContainerWidth(entry.contentRect.width);
        setContainerHeight(entry.contentRect.height);
      }
    });

    resizeObserver.observe(container);
    return () => resizeObserver.disconnect();
  }, []);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;
    container.addEventListener('scroll', handleScroll, { passive: true });
    return () => container.removeEventListener('scroll', handleScroll);
  }, [handleScroll]);

  const totalHeight = getTotalHeight();
  const visibleItems = getVisibleItems();

  return (
    <div
      ref={containerRef}
      className="w-full h-full overflow-y-auto"
      style={{ contain: 'strict' }}
    >
      <div
        className="relative w-full"
        style={{ height: `${totalHeight}px` }}
      >
        {visibleItems.map(({ index, top, height }) => {
          const photo = photos[index];
          const col = index % columnCount;
          const left = col * (itemWidth + gap);

          return (
            <div
              key={photo.id}
              className="absolute cursor-pointer"
              style={{
                top: `${top}px`,
                left: `${left}px`,
                width: `${itemWidth}px`,
                height: `${height}px`,
              }}
              onClick={() => onPhotoClick?.(photo)}
            >
              <ProgressiveImage
                src={photo.original_url}
                alt={`照片 ${index + 1}`}
                microSrc={photo.thumbnail_urls?.micro}
                thumbSrc={photo.thumbnail_urls?.thumb}
                mediumSrc={photo.thumbnail_urls?.medium}
                className="w-full h-full rounded-lg"
                placeholderClassName="rounded-lg"
                onLoad={handleImageLoad(index) as () => void}
                rootMargin="500px"
              />
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default VirtualPhotoGrid;
