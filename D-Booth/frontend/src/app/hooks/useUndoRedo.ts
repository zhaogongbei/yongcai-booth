import { useState, useCallback, useRef } from 'react';

export interface UndoRedoState<T> {
  past: T[];
  present: T;
  future: T[];
}

export function useUndoRedo<T>(initial: T, maxHistory = 50) {
  const [state, setState] = useState<UndoRedoState<T>>({
    past: [],
    present: initial,
    future: [],
  });

  // 使用ref跟踪debounce
  const debounceRef = useRef<NodeJS.Timeout | null>(null);
  const pendingRef = useRef<T | null>(null);

  const undo = useCallback(() => {
    setState(s => {
      if (s.past.length === 0) return s;
      const previous = s.past[s.past.length - 1];
      const newPast = s.past.slice(0, -1);
      return {
        past: newPast,
        present: previous,
        future: [s.present, ...s.future],
      };
    });
  }, []);

  const redo = useCallback(() => {
    setState(s => {
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

  const push = useCallback((newPresent: T) => {
    pendingRef.current = newPresent;
    if (debounceRef.current) {
      clearTimeout(debounceRef.current);
    }
    debounceRef.current = setTimeout(() => {
      setState(s => {
        const toSave = pendingRef.current;
        if (toSave === null) return s;
        pendingRef.current = null;
        const newPast = [...s.past, s.present].slice(-maxHistory);
        return {
          past: newPast,
          present: toSave,
          future: [],
        };
      });
    }, 200); // 200ms debounce: 连续操作合并为一个历史记录
  }, [maxHistory]);

  const reset = useCallback((newPresent: T) => {
    setState({
      past: [],
      present: newPresent,
      future: [],
    });
  }, []);

  const canUndo = state.past.length > 0;
  const canRedo = state.future.length > 0;

  return {
    present: state.present,
    set: push,
    undo,
    redo,
    reset,
    canUndo,
    canRedo,
  };
}