import { useState, useCallback, useRef, useEffect, useMemo } from 'react';

export interface UndoRedoState<T> {
  past: T[];
  present: T;
  future: T[];
}

export interface UndoRedoOptions {
  /** Maximum history entries to keep (default: 50) */
  maxHistory?: number;
  /** Debounce delay in milliseconds for consecutive changes (default: 200) */
  debounceDelay?: number;
  /** Custom equality function to detect changes (default: strict equality) */
  isEqual?: <T>(a: T, b: T) => boolean;
}

export interface UndoRedoReturn<T> {
  /** Current value */
  present: T;
  /** Update value (debounced) */
  set: (value: T) => void;
  /** Undo to previous state */
  undo: () => void;
  /** Redo to next state */
  redo: () => void;
  /** Reset history and set new present value */
  reset: (newPresent: T) => void;
  /** Clear all history but keep present value */
  clear: () => void;
  /** Whether undo is available */
  canUndo: boolean;
  /** Whether redo is available */
  canRedo: boolean;
  /** Number of undo steps available */
  undoCount: number;
  /** Number of redo steps available */
  redoCount: number;
}

/**
 * Undo/Redo state management hook
 *
 * Provides undo/redo functionality with debounced updates to merge rapid changes.
 * Useful for editors, canvas tools, and form state management.
 *
 * @param initial - Initial value
 * @param options - Configuration options
 * @returns Undo/redo state and control functions
 *
 * @example
 * ```tsx
 * function TextEditor() {
 *   const editor = useUndoRedo('', { maxHistory: 100, debounceDelay: 300 });
 *
 *   return (
 *     <div>
 *       <textarea
 *         value={editor.present}
 *         onChange={(e) => editor.set(e.target.value)}
 *       />
 *       <button onClick={editor.undo} disabled={!editor.canUndo}>
 *         Undo ({editor.undoCount})
 *       </button>
 *       <button onClick={editor.redo} disabled={!editor.canRedo}>
 *         Redo ({editor.redoCount})
 *       </button>
 *       <button onClick={editor.clear}>Clear History</button>
 *     </div>
 *   );
 * }
 * ```
 */
export function useUndoRedo<T>(
  initial: T,
  options: UndoRedoOptions = {}
): UndoRedoReturn<T> {
  const {
    maxHistory = 50,
    debounceDelay = 200,
    isEqual = (a, b) => a === b,
  } = options;

  const [state, setState] = useState<UndoRedoState<T>>({
    past: [],
    present: initial,
    future: [],
  });

  // Track debounce timer and pending value
  const debounceRef = useRef<NodeJS.Timeout | null>(null);
  const pendingRef = useRef<T | null>(null);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (debounceRef.current) {
        clearTimeout(debounceRef.current);
      }
    };
  }, []);

  const undo = useCallback(() => {
    // Flush any pending changes before undo
    if (debounceRef.current) {
      clearTimeout(debounceRef.current);
      debounceRef.current = null;
      if (pendingRef.current !== null) {
        const toSave = pendingRef.current;
        pendingRef.current = null;
        setState((s) => {
          if (isEqual(s.present, toSave)) return s;
          const newPast = [...s.past, s.present].slice(-maxHistory);
          return {
            past: newPast,
            present: toSave,
            future: [],
          };
        });
        // Don't undo immediately after flush, wait for next call
        return;
      }
    }

    setState((s) => {
      if (s.past.length === 0) return s;
      const previous = s.past[s.past.length - 1];
      const newPast = s.past.slice(0, -1);
      return {
        past: newPast,
        present: previous,
        future: [s.present, ...s.future],
      };
    });
  }, [isEqual, maxHistory]);

  const redo = useCallback(() => {
    // Flush any pending changes before redo
    if (debounceRef.current) {
      clearTimeout(debounceRef.current);
      debounceRef.current = null;
      pendingRef.current = null;
    }

    setState((s) => {
      if (s.future.length === 0) return s;
      const next = s.future[0];
      const newFuture = s.future.slice(1);
      return {
        past: [...s.past, s.present],
        present: next,
        future: newFuture,
      };
    });
  }, []);

  const push = useCallback(
    (newPresent: T) => {
      pendingRef.current = newPresent;

      if (debounceRef.current) {
        clearTimeout(debounceRef.current);
      }

      debounceRef.current = setTimeout(() => {
        setState((s) => {
          const toSave = pendingRef.current;
          if (toSave === null) return s;
          pendingRef.current = null;

          // Skip if value hasn't changed
          if (isEqual(s.present, toSave)) {
            return s;
          }

          const newPast = [...s.past, s.present].slice(-maxHistory);
          return {
            past: newPast,
            present: toSave,
            future: [], // Clear future on new change
          };
        });
      }, debounceDelay);
    },
    [maxHistory, debounceDelay, isEqual]
  );

  const reset = useCallback((newPresent: T) => {
    // Clear pending changes
    if (debounceRef.current) {
      clearTimeout(debounceRef.current);
      debounceRef.current = null;
    }
    pendingRef.current = null;

    setState({
      past: [],
      present: newPresent,
      future: [],
    });
  }, []);

  const clear = useCallback(() => {
    // Clear pending changes
    if (debounceRef.current) {
      clearTimeout(debounceRef.current);
      debounceRef.current = null;
    }
    pendingRef.current = null;

    setState((s) => ({
      past: [],
      present: s.present,
      future: [],
    }));
  }, []);

  // Memoize computed values
  const canUndo = useMemo(() => state.past.length > 0, [state.past.length]);
  const canRedo = useMemo(() => state.future.length > 0, [state.future.length]);
  const undoCount = useMemo(() => state.past.length, [state.past.length]);
  const redoCount = useMemo(() => state.future.length, [state.future.length]);

  return {
    present: state.present,
    set: push,
    undo,
    redo,
    reset,
    clear,
    canUndo,
    canRedo,
    undoCount,
    redoCount,
  };
}