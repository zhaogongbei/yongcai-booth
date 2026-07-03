import { useState, useEffect, useCallback, useRef } from 'react';

/**
 * Options for useLocalStorage hook
 */
export interface UseLocalStorageOptions<T> {
  /** Serializer function (default: JSON.stringify) */
  serializer?: (value: T) => string;
  /** Deserializer function (default: JSON.parse) */
  deserializer?: (value: string) => T;
  /** Whether to sync across tabs/windows (default: true) */
  syncAcrossTabs?: boolean;
  /** Error handler callback */
  onError?: (error: Error) => void;
}

/**
 * Local storage hook with automatic serialization and cross-tab synchronization
 *
 * Provides a React state-like interface for localStorage with automatic JSON
 * serialization, type safety, and synchronization across browser tabs.
 *
 * @param key - localStorage key
 * @param initialValue - Default value if key doesn't exist
 * @param options - Configuration options
 * @returns Current value, setter function, and remove function
 *
 * @example
 * ```tsx
 * // Basic usage
 * function ThemeSelector() {
 *   const [theme, setTheme, removeTheme] = useLocalStorage('theme', 'light');
 *
 *   return (
 *     <div>
 *       <p>Current theme: {theme}</p>
 *       <button onClick={() => setTheme('dark')}>Dark Mode</button>
 *       <button onClick={() => setTheme('light')}>Light Mode</button>
 *       <button onClick={removeTheme}>Reset</button>
 *     </div>
 *   );
 * }
 *
 * // With complex objects
 * interface UserPreferences {
 *   language: string;
 *   notifications: boolean;
 *   volume: number;
 * }
 *
 * function Preferences() {
 *   const [prefs, setPrefs] = useLocalStorage<UserPreferences>(
 *     'user-prefs',
 *     { language: 'en', notifications: true, volume: 50 }
 *   );
 *
 *   return (
 *     <div>
 *       <select
 *         value={prefs.language}
 *         onChange={e => setPrefs({ ...prefs, language: e.target.value })}
 *       >
 *         <option value="en">English</option>
 *         <option value="zh">中文</option>
 *       </select>
 *     </div>
 *   );
 * }
 *
 * // With custom serialization
 * function DatePicker() {
 *   const [date, setDate] = useLocalStorage<Date>(
 *     'selected-date',
 *     new Date(),
 *     {
 *       serializer: (date) => date.toISOString(),
 *       deserializer: (str) => new Date(str),
 *     }
 *   );
 *
 *   return <input type="date" value={date.toISOString().split('T')[0]} />;
 * }
 * ```
 */
export function useLocalStorage<T>(
  key: string,
  initialValue: T,
  options: UseLocalStorageOptions<T> = {}
): [T, (value: T | ((prev: T) => T)) => void, () => void] {
  const {
    serializer = JSON.stringify,
    deserializer = JSON.parse,
    syncAcrossTabs = true,
    onError,
  } = options;

  // Track if component is mounted
  const mountedRef = useRef(true);

  // Read from localStorage
  const readValue = useCallback((): T => {
    if (typeof window === 'undefined') {
      return initialValue;
    }

    try {
      const item = window.localStorage.getItem(key);
      return item ? deserializer(item) : initialValue;
    } catch (error) {
      const err = error instanceof Error ? error : new Error('Failed to read from localStorage');
      onError?.(err);
      console.warn(`Error reading localStorage key "${key}":`, error);
      return initialValue;
    }
  }, [key, initialValue, deserializer, onError]);

  const [storedValue, setStoredValue] = useState<T>(readValue);

  // Write to localStorage
  const setValue = useCallback(
    (value: T | ((prev: T) => T)) => {
      if (typeof window === 'undefined') {
        console.warn('localStorage is not available');
        return;
      }

      try {
        // Allow value to be a function like useState
        const valueToStore = value instanceof Function ? value(storedValue) : value;

        // Save to state
        if (mountedRef.current) {
          setStoredValue(valueToStore);
        }

        // Save to localStorage
        window.localStorage.setItem(key, serializer(valueToStore));

        // Dispatch custom event for cross-tab sync
        if (syncAcrossTabs) {
          window.dispatchEvent(
            new CustomEvent('local-storage-change', {
              detail: { key, value: valueToStore },
            })
          );
        }
      } catch (error) {
        const err = error instanceof Error ? error : new Error('Failed to write to localStorage');
        onError?.(err);
        console.warn(`Error setting localStorage key "${key}":`, error);
      }
    },
    [key, storedValue, serializer, syncAcrossTabs, onError]
  );

  // Remove from localStorage
  const removeValue = useCallback(() => {
    if (typeof window === 'undefined') {
      console.warn('localStorage is not available');
      return;
    }

    try {
      window.localStorage.removeItem(key);

      // Reset to initial value
      if (mountedRef.current) {
        setStoredValue(initialValue);
      }

      // Dispatch custom event for cross-tab sync
      if (syncAcrossTabs) {
        window.dispatchEvent(
          new CustomEvent('local-storage-change', {
            detail: { key, value: undefined },
          })
        );
      }
    } catch (error) {
      const err = error instanceof Error ? error : new Error('Failed to remove from localStorage');
      onError?.(err);
      console.warn(`Error removing localStorage key "${key}":`, error);
    }
  }, [key, initialValue, syncAcrossTabs, onError]);

  // Sync across tabs using storage event
  useEffect(() => {
    if (!syncAcrossTabs) return;

    const handleStorageChange = (e: StorageEvent) => {
      if (e.key === key && e.newValue !== null) {
        try {
          const newValue = deserializer(e.newValue);
          if (mountedRef.current) {
            setStoredValue(newValue);
          }
        } catch (error) {
          const err = error instanceof Error ? error : new Error('Failed to sync from other tab');
          onError?.(err);
          console.warn(`Error syncing localStorage key "${key}":`, error);
        }
      } else if (e.key === key && e.newValue === null) {
        // Key was removed in another tab
        if (mountedRef.current) {
          setStoredValue(initialValue);
        }
      }
    };

    const handleCustomStorageChange = (e: Event) => {
      const customEvent = e as CustomEvent<{ key: string; value: T | undefined }>;
      if (customEvent.detail.key === key) {
        if (customEvent.detail.value !== undefined && mountedRef.current) {
          setStoredValue(customEvent.detail.value);
        } else if (customEvent.detail.value === undefined && mountedRef.current) {
          setStoredValue(initialValue);
        }
      }
    };

    window.addEventListener('storage', handleStorageChange);
    window.addEventListener('local-storage-change', handleCustomStorageChange);

    return () => {
      window.removeEventListener('storage', handleStorageChange);
      window.removeEventListener('local-storage-change', handleCustomStorageChange);
    };
  }, [key, initialValue, deserializer, syncAcrossTabs, onError]);

  // Cleanup on unmount
  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
    };
  }, []);

  return [storedValue, setValue, removeValue];
}

/**
 * Session storage hook (same API as useLocalStorage but uses sessionStorage)
 *
 * Data persists only for the current browser session (cleared when tab is closed)
 *
 * @param key - sessionStorage key
 * @param initialValue - Default value if key doesn't exist
 * @param options - Configuration options (syncAcrossTabs is ignored)
 * @returns Current value, setter function, and remove function
 *
 * @example
 * ```tsx
 * function FormWizard() {
 *   const [currentStep, setCurrentStep] = useSessionStorage('wizard-step', 1);
 *
 *   return <div>Step {currentStep} of 5</div>;
 * }
 * ```
 */
export function useSessionStorage<T>(
  key: string,
  initialValue: T,
  options: Omit<UseLocalStorageOptions<T>, 'syncAcrossTabs'> = {}
): [T, (value: T | ((prev: T) => T)) => void, () => void] {
  const { serializer = JSON.stringify, deserializer = JSON.parse, onError } = options;

  const mountedRef = useRef(true);

  const readValue = useCallback((): T => {
    if (typeof window === 'undefined') {
      return initialValue;
    }

    try {
      const item = window.sessionStorage.getItem(key);
      return item ? deserializer(item) : initialValue;
    } catch (error) {
      const err = error instanceof Error ? error : new Error('Failed to read from sessionStorage');
      onError?.(err);
      console.warn(`Error reading sessionStorage key "${key}":`, error);
      return initialValue;
    }
  }, [key, initialValue, deserializer, onError]);

  const [storedValue, setStoredValue] = useState<T>(readValue);

  const setValue = useCallback(
    (value: T | ((prev: T) => T)) => {
      if (typeof window === 'undefined') {
        console.warn('sessionStorage is not available');
        return;
      }

      try {
        const valueToStore = value instanceof Function ? value(storedValue) : value;

        if (mountedRef.current) {
          setStoredValue(valueToStore);
        }

        window.sessionStorage.setItem(key, serializer(valueToStore));
      } catch (error) {
        const err = error instanceof Error ? error : new Error('Failed to write to sessionStorage');
        onError?.(err);
        console.warn(`Error setting sessionStorage key "${key}":`, error);
      }
    },
    [key, storedValue, serializer, onError]
  );

  const removeValue = useCallback(() => {
    if (typeof window === 'undefined') {
      console.warn('sessionStorage is not available');
      return;
    }

    try {
      window.sessionStorage.removeItem(key);

      if (mountedRef.current) {
        setStoredValue(initialValue);
      }
    } catch (error) {
      const err = error instanceof Error ? error : new Error('Failed to remove from sessionStorage');
      onError?.(err);
      console.warn(`Error removing sessionStorage key "${key}":`, error);
    }
  }, [key, initialValue, onError]);

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
    };
  }, []);

  return [storedValue, setValue, removeValue];
}
