import { useCallback, useState } from 'react';

export type UseToggleReturn = [
  value: boolean,
  toggle: () => void,
  setTrue: () => void,
  setFalse: () => void,
  setValue: (value: boolean) => void,
];

/**
 * Boolean state helper for common UI controls such as modals and dropdowns.
 */
export function useToggle(initialValue = false): UseToggleReturn {
  const [value, setValue] = useState<boolean>(initialValue);

  const toggle = useCallback(() => {
    setValue((current) => !current);
  }, []);

  const setTrue = useCallback(() => {
    setValue(true);
  }, []);

  const setFalse = useCallback(() => {
    setValue(false);
  }, []);

  return [value, toggle, setTrue, setFalse, setValue];
}

/**
 * Manage a keyed set of boolean states.
 */
export function useMultiToggle<T extends Record<string, boolean>>(initialStates: T) {
  const [states, setStates] = useState<T>(initialStates);

  const toggle = useCallback((key: keyof T) => {
    setStates((current) => ({
      ...current,
      [key]: !current[key],
    }));
  }, []);

  const setTrue = useCallback((key: keyof T) => {
    setStates((current) => ({
      ...current,
      [key]: true,
    }));
  }, []);

  const setFalse = useCallback((key: keyof T) => {
    setStates((current) => ({
      ...current,
      [key]: false,
    }));
  }, []);

  const setValue = useCallback((key: keyof T, value: boolean) => {
    setStates((current) => ({
      ...current,
      [key]: value,
    }));
  }, []);

  const setAllTrue = useCallback(() => {
    setStates((current) =>
      Object.fromEntries(Object.keys(current).map((key) => [key, true])) as T
    );
  }, []);

  const setAllFalse = useCallback(() => {
    setStates((current) =>
      Object.fromEntries(Object.keys(current).map((key) => [key, false])) as T
    );
  }, []);

  const reset = useCallback(() => {
    setStates(initialStates);
  }, [initialStates]);

  return {
    states,
    toggle,
    setTrue,
    setFalse,
    setValue,
    setAllTrue,
    setAllFalse,
    reset,
  };
}
