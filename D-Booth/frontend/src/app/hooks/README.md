# Frontend Custom Hooks

## Overview

This directory contains reusable React custom hooks for the D-Booth frontend application. Each hook is designed with TypeScript, comprehensive error handling, performance optimization, and detailed documentation.

## Available Hooks

### Data Fetching & State Management

#### `useApi`
HTTP API request management with automatic loading, error, and data state tracking.

```tsx
const { data, loading, error, execute, refresh } = useApi<User>('/users/123');
```

**Features:**
- Automatic/manual execution
- Request cancellation on unmount
- Debouncing support
- Success/error callbacks
- HTTP method helpers: `useGet`, `usePost`, `usePut`, `useDelete`

#### `useAsync`
Generic async operation management for any async function.

```tsx
const { data, loading, error, execute, retry } = useAsync(
  async (id: string) => fetchUser(id),
  { immediate: true, deps: [userId] }
);
```

**Features:**
- Loading/error/success states
- Retry functionality
- Component unmount cleanup
- Type-safe execution

#### `useFetch`
Simplified async data fetching helper that executes on mount and exposes refetching.

```tsx
const { data, loading, error, refetch } = useFetch(fetchUsers, []);
```

**Features:**
- Automatic execution on mount
- Dependency-based refetching
- Loading/error/success states
- Manual `refetch()` helper

#### `useHttpFetch`
URL-based HTTP fetch hook for components that need request status, query params, timeout, retry, cancellation, and non-GET helpers.

```tsx
const { data, loading, error, status, refetch } = useHttpFetch<User>('/api/users/123');
```

**Features:**
- HTTP status and status text tracking
- Query parameter serialization
- Request timeout and cancellation
- Retry support with configurable delay
- Method helpers: `useHttpGet`, `useHttpPost`, `useHttpPut`, `useHttpPatch`, `useHttpDelete`

### Authentication

#### `useAuth`
Authentication state management with login/logout and automatic token refresh.

```tsx
const { isAuthenticated, login, logout, isLoading, error } = useAuth();
```

**Features:**
- Token storage management
- Unauthorized event handling
- Loading states
- Error handling

### Form Management

#### `useForm`
Comprehensive form state management with validation, error handling, and field tracking.

```tsx
const form = useForm<LoginForm>({
  initialValues: { username: '', password: '' },
  fields: {
    username: {
      validate: (value) => value ? null : 'Required',
    },
  },
  onSubmit: async (values) => {
    await login(values);
  },
});
```

**Features:**
- Field-level validation (sync/async)
- Form-level validation
- Touched/dirty state tracking
- Submit handling
- Field props helpers: `getFieldProps()`

### UI & Interaction

#### `useToggle`
Boolean state management with convenient toggle and set helpers.

```tsx
const [isOpen, toggle, open, close] = useToggle(false);
```

**Features:**
- Simple boolean state management
- Toggle, setTrue, setFalse helpers
- Multi-toggle support: `useMultiToggle`
- Ideal for modals, dropdowns, accordions

#### `useResponsive`
Responsive design hook with breakpoint detection and orientation tracking.

```tsx
const { isMobile, isTablet, isDesktop, orientation, width, height } = useResponsive();
```

**Features:**
- Breakpoint detection (mobile/tablet/desktop)
- Orientation tracking (portrait/landscape)
- Window dimensions
- Debounced resize events
- SSR-safe

#### `useDebounce`
Value and callback debouncing for performance optimization.

```tsx
const debouncedValue = useDebounce(searchQuery, 500);
const [debouncedSave, cancelSave] = useDebouncedCallback(saveData, 1000);
```

**Features:**
- Value debouncing
- Callback debouncing with cancellation
- Throttled callbacks: `useThrottledCallback`

#### `useUndoRedo`
Undo/redo state management with history tracking.

```tsx
const editor = useUndoRedo('initial text', {
  maxHistory: 100,
  debounceDelay: 300,
});
```

**Features:**
- History management (past/present/future)
- Debounced updates
- Configurable history size
- Clear/reset functionality
- Undo/redo count tracking

#### `usePagination`
Client-side and server-side pagination management.

```tsx
const pagination = usePagination({
  initialPage: 1,
  pageSize: 20,
  totalItems: 100,
});
```

**Features:**
- Page navigation (first/prev/next/last)
- Page size management
- Index calculation
- Helper: `getPageNumbers()` for pagination UI

### Storage

#### `useLocalStorage` / `useSessionStorage`
Persistent state management with localStorage/sessionStorage.

```tsx
const [theme, setTheme, removeTheme] = useLocalStorage('theme', 'light');
```

**Features:**
- Automatic JSON serialization
- Cross-tab synchronization (localStorage)
- Custom serialization support
- SSR-safe
- Error handling

### Real-time Communication

#### `useWebSocket`
WebSocket connection management with automatic reconnection and heartbeat.

```tsx
const ws = useWebSocket<ChatMessage>('ws://localhost:8080/chat', {
  autoReconnect: true,
  heartbeatInterval: 30000,
  onMessage: (msg) => console.log(msg),
});
```

**Features:**
- Connection state management
- Automatic reconnection with exponential backoff
- Heartbeat/ping mechanism
- Message history
- Type-safe message parsing
- Connection control methods

### Application-Specific

#### `useBoothHealth`
Booth system health monitoring (API, camera, printers).

```tsx
const health = useBoothHealth(selectedPrinterName);
```

**Features:**
- Real-time health checks
- Component status tracking
- Print queue management
- Auto-refresh (8s for health, 5s for queue)

## Optimization Features

### Performance
- **Memoization**: All hooks use `useMemo` and `useCallback` appropriately
- **Debouncing**: Built-in debouncing for frequent operations
- **Cleanup**: Proper cleanup on component unmount
- **Ref Management**: Using refs to avoid unnecessary re-renders

### Error Handling
- Try-catch blocks for all async operations
- Error callbacks for custom handling
- Console warnings for debugging
- Type-safe error states

### TypeScript
- Full type safety with generics
- Comprehensive type exports
- Inferred return types
- Strict type checking

### SSR Safety
- `typeof window` checks
- Safe default values
- Conditional effects

## Usage Guidelines

### Import Pattern

```tsx
// Import specific hooks
import { useApi, useDebounce, useForm } from '@/app/hooks';

// Import types
import type { ApiState, FormConfig } from '@/app/hooks';
```

### Best Practices

1. **Always handle loading states**
   ```tsx
   if (loading) return <Spinner />;
   if (error) return <ErrorMessage error={error} />;
   ```

2. **Use appropriate cleanup**
   ```tsx
   // Hooks handle cleanup automatically
   const { data } = useApi('/endpoint'); // Cancels on unmount
   ```

3. **Leverage TypeScript**
   ```tsx
   interface User { id: string; name: string; }
   const { data } = useApi<User>('/user'); // data is User | null
   ```

4. **Combine hooks for complex logic**
   ```tsx
   const { data: users } = useApi<User[]>('/users');
   const pagination = usePagination({ totalItems: users?.length || 0 });
   const currentUsers = users?.slice(pagination.startIndex, pagination.endIndex + 1);
   ```

## Testing

Each hook should be tested with:
- Loading states
- Success scenarios
- Error scenarios
- Cleanup behavior
- Edge cases (unmount during operation, rapid state changes)

## Contributing

When adding new hooks:
1. Follow existing patterns and conventions
2. Add comprehensive JSDoc comments
3. Include usage examples in comments
4. Export types from `index.ts`
5. Add entry to this README
6. Ensure TypeScript strict mode compliance
7. Add proper error handling
8. Include cleanup logic
