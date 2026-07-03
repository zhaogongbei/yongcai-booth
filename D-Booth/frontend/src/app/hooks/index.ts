/**
 * Custom React Hooks for D-Booth
 *
 * Re-exports all custom hooks for easy importing
 */

export { useAuth } from './useAuth';
export type { AuthState, LoginParams } from './useAuth';

export { useApi, useGet, usePost, usePut, useDelete } from './useApi';
export type { ApiState, UseApiOptions } from './useApi';

export { useAsync, useFetch } from './useAsync';
export type { AsyncState, UseAsyncOptions } from './useAsync';

export {
  HttpFetchError,
  useHttpDelete,
  useHttpFetch,
  useHttpGet,
  useHttpPatch,
  useHttpPost,
  useHttpPut,
} from './useHttpFetch';
export type { HttpFetchState, HttpMethod, UseHttpFetchOptions } from './useHttpFetch';

export { useDebounce, useDebouncedCallback, useThrottledCallback } from './useDebounce';

export { useForm } from './useForm';
export type {
  FormConfig,
  FormState,
  FieldConfig,
  FieldState,
  Validator,
} from './useForm';

export { useLocalStorage, useSessionStorage } from './useLocalStorage';
export type { UseLocalStorageOptions } from './useLocalStorage';

export { usePagination, getPageNumbers } from './usePagination';
export type { PaginationOptions, PaginationState } from './usePagination';

export { useBoothHealth, apiTone, cameraTone, printerTone } from './useBoothHealth';
export type { HealthTone, CameraHealth, BoothHealth } from './useBoothHealth';

export { useResponsive } from './useResponsive';
export type { ResponsiveState } from './useResponsive';

export { useUndoRedo } from './useUndoRedo';
export type { UndoRedoState, UndoRedoOptions, UndoRedoReturn } from './useUndoRedo';

export { useWebSocket } from './useWebSocket';
export type {
  WebSocketState,
  WebSocketMessage,
  UseWebSocketOptions,
  UseWebSocketReturn,
} from './useWebSocket';

export { useToggle, useMultiToggle } from './useToggle';
export type { UseToggleReturn } from './useToggle';
