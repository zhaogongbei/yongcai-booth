/**
 * Custom React Hooks for D-Booth
 *
 * Re-exports all custom hooks for easy importing
 */

export { useAuth } from './useAuth';
export type { AuthState, LoginParams } from './useAuth';

export { useApi, useGet, usePost, usePut, useDelete } from './useApi';
export type { ApiState, UseApiOptions } from './useApi';

export { useDebounce, useDebouncedCallback, useThrottledCallback } from './useDebounce';

export { useLocalStorage, useSessionStorage } from './useLocalStorage';
export type { UseLocalStorageOptions } from './useLocalStorage';

export { usePagination, getPageNumbers } from './usePagination';
export type { PaginationOptions, PaginationState } from './usePagination';

export { useBoothHealth, apiTone, cameraTone, printerTone } from './useBoothHealth';
export type { HealthTone, CameraHealth, BoothHealth } from './useBoothHealth';

export { useResponsive } from './useResponsive';

export { useUndoRedo } from './useUndoRedo';
export type { UndoRedoState } from './useUndoRedo';
