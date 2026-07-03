import { useState, useEffect, useRef } from 'react';

/**
 * Debounce a value
 *
 * Returns a debounced version of the input value that only updates after
 * the specified delay has passed without the value changing.
 *
 * @param value - The value to debounce
 * @param delay - Delay in milliseconds (default: 300)
 * @returns Debounced value
 *
 * @example
 * ```tsx
 * function SearchBox() {
 *   const [query, setQuery] = useState('');
 *   const debouncedQuery = useDebounce(query, 500);
 *
 *   // Only fetch when user stops typing for 500ms
 *   useEffect(() => {
 *     if (debouncedQuery) {
 *       fetchResults(debouncedQuery);
 *     }
 *   }, [debouncedQuery]);
 *
 *   return <input value={query} onChange={e => setQuery(e.target.value)} />;
 * }
 * ```
 */
export function useDebounce<T>(value: T, delay: number = 300): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value);
  const timerRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    // Clear previous timer
    if (timerRef.current) {
      clearTimeout(timerRef.current);
    }

    // Set new timer
    timerRef.current = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    // Cleanup on unmount or value change
    return () => {
      if (timerRef.current) {
        clearTimeout(timerRef.current);
      }
    };
  }, [value, delay]);

  return debouncedValue;
}

/**
 * Debounce a callback function
 *
 * Returns a debounced version of the callback that will only execute after
 * the specified delay has passed since the last invocation.
 *
 * @param callback - The function to debounce
 * @param delay - Delay in milliseconds (default: 300)
 * @returns Debounced callback and cancel function
 *
 * @example
 * ```tsx
 * function AutoSaveForm() {
 *   const [formData, setFormData] = useState({ name: '', email: '' });
 *
 *   const saveToBackend = async (data: typeof formData) => {
 *     await fetch('/api/save', { method: 'POST', body: JSON.stringify(data) });
 *   };
 *
 *   const [debouncedSave, cancelSave] = useDebouncedCallback(saveToBackend, 1000);
 *
 *   const handleChange = (field: string, value: string) => {
 *     const updated = { ...formData, [field]: value };
 *     setFormData(updated);
 *     debouncedSave(updated);
 *   };
 *
 *   return (
 *     <form>
 *       <input
 *         value={formData.name}
 *         onChange={e => handleChange('name', e.target.value)}
 *       />
 *       <button type="button" onClick={cancelSave}>Cancel Auto-save</button>
 *     </form>
 *   );
 * }
 * ```
 */
export function useDebouncedCallback<T extends (...args: any[]) => any>(
  callback: T,
  delay: number = 300
): [(...args: Parameters<T>) => void, () => void] {
  const timerRef = useRef<NodeJS.Timeout | null>(null);
  const callbackRef = useRef(callback);

  // Keep callback ref up to date
  useEffect(() => {
    callbackRef.current = callback;
  }, [callback]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (timerRef.current) {
        clearTimeout(timerRef.current);
      }
    };
  }, []);

  const debouncedCallback = (...args: Parameters<T>) => {
    // Clear previous timer
    if (timerRef.current) {
      clearTimeout(timerRef.current);
    }

    // Set new timer
    timerRef.current = setTimeout(() => {
      callbackRef.current(...args);
    }, delay);
  };

  const cancel = () => {
    if (timerRef.current) {
      clearTimeout(timerRef.current);
      timerRef.current = null;
    }
  };

  return [debouncedCallback, cancel];
}

/**
 * Throttle a callback function
 *
 * Returns a throttled version of the callback that will execute at most once
 * per the specified interval.
 *
 * @param callback - The function to throttle
 * @param limit - Minimum time between executions in milliseconds (default: 300)
 * @returns Throttled callback
 *
 * @example
 * ```tsx
 * function ScrollListener() {
 *   const handleScroll = useThrottledCallback(() => {
 *     console.log('Scroll position:', window.scrollY);
 *   }, 200);
 *
 *   useEffect(() => {
 *     window.addEventListener('scroll', handleScroll);
 *     return () => window.removeEventListener('scroll', handleScroll);
 *   }, [handleScroll]);
 *
 *   return <div>Scroll to see throttled logs</div>;
 * }
 * ```
 */
export function useThrottledCallback<T extends (...args: any[]) => any>(
  callback: T,
  limit: number = 300
): (...args: Parameters<T>) => void {
  const inThrottleRef = useRef(false);
  const callbackRef = useRef(callback);

  // Keep callback ref up to date
  useEffect(() => {
    callbackRef.current = callback;
  }, [callback]);

  return (...args: Parameters<T>) => {
    if (!inThrottleRef.current) {
      callbackRef.current(...args);
      inThrottleRef.current = true;
      setTimeout(() => {
        inThrottleRef.current = false;
      }, limit);
    }
  };
}
