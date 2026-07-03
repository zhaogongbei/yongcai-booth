import { useState, useEffect, useCallback, useRef, useMemo } from 'react';

type Breakpoint = 'mobile' | 'tablet' | 'desktop';
type Orientation = 'portrait' | 'landscape';

export interface ResponsiveState {
  breakpoint: Breakpoint;
  isMobile: boolean;
  isTablet: boolean;
  isDesktop: boolean;
  orientation: Orientation;
  width: number;
  height: number;
}

/**
 * Responsive design hook with breakpoint detection and orientation tracking
 *
 * Provides real-time viewport information including breakpoints, orientation,
 * and dimensions. Automatically debounces resize events for performance.
 *
 * @returns Current responsive state
 *
 * @example
 * ```tsx
 * function ResponsiveComponent() {
 *   const { isMobile, isTablet, isDesktop, orientation } = useResponsive();
 *
 *   if (isMobile) {
 *     return <MobileLayout />;
 *   }
 *
 *   return <DesktopLayout />;
 * }
 * ```
 */
export function useResponsive(): ResponsiveState {
  // Initialize with SSR-safe defaults
  const getInitialBreakpoint = (): Breakpoint => {
    if (typeof window === 'undefined') return 'desktop';
    const width = window.innerWidth;
    if (width < 768) return 'mobile';
    if (width <= 1024) return 'tablet';
    return 'desktop';
  };

  const getInitialOrientation = (): Orientation => {
    if (typeof window === 'undefined') return 'landscape';
    return window.matchMedia('(orientation: portrait)').matches ? 'portrait' : 'landscape';
  };

  const [breakpoint, setBreakpoint] = useState<Breakpoint>(getInitialBreakpoint);
  const [orientation, setOrientation] = useState<Orientation>(getInitialOrientation);
  const [dimensions, setDimensions] = useState({
    width: typeof window !== 'undefined' ? window.innerWidth : 0,
    height: typeof window !== 'undefined' ? window.innerHeight : 0,
  });

  const debounceTimerRef = useRef<NodeJS.Timeout | null>(null);

  const handleResize = useCallback(() => {
    if (typeof window === 'undefined') return;

    const width = window.innerWidth;
    const height = window.innerHeight;

    // Update breakpoint
    if (width < 768) {
      setBreakpoint('mobile');
    } else if (width <= 1024) {
      setBreakpoint('tablet');
    } else {
      setBreakpoint('desktop');
    }

    // Update orientation
    const isPortrait = window.matchMedia('(orientation: portrait)').matches;
    setOrientation(isPortrait ? 'portrait' : 'landscape');

    // Update dimensions
    setDimensions({ width, height });
  }, []);

  const debouncedHandleResize = useCallback(() => {
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
    }

    debounceTimerRef.current = setTimeout(() => {
      handleResize();
    }, 150);
  }, [handleResize]);

  useEffect(() => {
    if (typeof window === 'undefined') return;

    // Initial measurement
    handleResize();

    // Add event listeners with debouncing
    window.addEventListener('resize', debouncedHandleResize);
    window.addEventListener('orientationchange', handleResize); // No debounce for orientation

    return () => {
      window.removeEventListener('resize', debouncedHandleResize);
      window.removeEventListener('orientationchange', handleResize);
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }
    };
  }, [handleResize, debouncedHandleResize]);

  // Memoize computed values
  const state = useMemo<ResponsiveState>(
    () => ({
      breakpoint,
      isMobile: breakpoint === 'mobile',
      isTablet: breakpoint === 'tablet',
      isDesktop: breakpoint === 'desktop',
      orientation,
      width: dimensions.width,
      height: dimensions.height,
    }),
    [breakpoint, orientation, dimensions]
  );

  return state;
}
