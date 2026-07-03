import { useState, useMemo, useCallback } from 'react';

/**
 * Pagination configuration options
 */
export interface PaginationOptions {
  /** Initial page number (1-indexed, default: 1) */
  initialPage?: number;
  /** Items per page (default: 10) */
  pageSize?: number;
  /** Total number of items */
  totalItems?: number;
}

/**
 * Pagination state and controls
 */
export interface PaginationState {
  /** Current page number (1-indexed) */
  currentPage: number;
  /** Items per page */
  pageSize: number;
  /** Total number of pages */
  totalPages: number;
  /** Total number of items */
  totalItems: number;
  /** Index of first item on current page (0-indexed) */
  startIndex: number;
  /** Index of last item on current page (0-indexed, inclusive) */
  endIndex: number;
  /** Whether there is a previous page */
  hasPreviousPage: boolean;
  /** Whether there is a next page */
  hasNextPage: boolean;
  /** Go to a specific page */
  goToPage: (page: number) => void;
  /** Go to next page */
  nextPage: () => void;
  /** Go to previous page */
  previousPage: () => void;
  /** Go to first page */
  firstPage: () => void;
  /** Go to last page */
  lastPage: () => void;
  /** Change page size */
  setPageSize: (size: number) => void;
  /** Update total items count */
  setTotalItems: (total: number) => void;
  /** Reset to initial state */
  reset: () => void;
}

/**
 * Pagination hook for managing paginated data
 *
 * Provides state and controls for client-side or server-side pagination,
 * including page navigation, page size management, and pagination metadata.
 *
 * @param options - Pagination configuration
 * @returns Pagination state and control functions
 *
 * @example
 * ```tsx
 * // Client-side pagination
 * function UserTable({ users }: { users: User[] }) {
 *   const pagination = usePagination({
 *     initialPage: 1,
 *     pageSize: 20,
 *     totalItems: users.length,
 *   });
 *
 *   const currentUsers = users.slice(
 *     pagination.startIndex,
 *     pagination.endIndex + 1
 *   );
 *
 *   return (
 *     <div>
 *       <table>
 *         {currentUsers.map(user => (
 *           <tr key={user.id}>{user.name}</tr>
 *         ))}
 *       </table>
 *
 *       <div>
 *         <button onClick={pagination.previousPage} disabled={!pagination.hasPreviousPage}>
 *           Previous
 *         </button>
 *         <span>
 *           Page {pagination.currentPage} of {pagination.totalPages}
 *         </span>
 *         <button onClick={pagination.nextPage} disabled={!pagination.hasNextPage}>
 *           Next
 *         </button>
 *       </div>
 *     </div>
 *   );
 * }
 *
 * // Server-side pagination
 * function ServerPaginatedList() {
 *   const pagination = usePagination({
 *     initialPage: 1,
 *     pageSize: 50,
 *     totalItems: 0, // Will be updated from API response
 *   });
 *
 *   const { data, loading } = useApi<{ items: Item[], total: number }>(
 *     '/items',
 *     {
 *       query: {
 *         page: pagination.currentPage,
 *         page_size: pagination.pageSize,
 *       },
 *       deps: [pagination.currentPage, pagination.pageSize],
 *       onSuccess: (response) => {
 *         pagination.setTotalItems(response.total);
 *       },
 *     }
 *   );
 *
 *   if (loading) return <Spinner />;
 *
 *   return (
 *     <div>
 *       {data?.items.map(item => <ItemCard key={item.id} item={item} />)}
 *       <Pagination {...pagination} />
 *     </div>
 *   );
 * }
 *
 * // With page size selector
 * function DataGrid({ data }: { data: any[] }) {
 *   const pagination = usePagination({
 *     pageSize: 25,
 *     totalItems: data.length,
 *   });
 *
 *   return (
 *     <div>
 *       <select
 *         value={pagination.pageSize}
 *         onChange={(e) => pagination.setPageSize(Number(e.target.value))}
 *       >
 *         <option value={10}>10 per page</option>
 *         <option value={25}>25 per page</option>
 *         <option value={50}>50 per page</option>
 *         <option value={100}>100 per page</option>
 *       </select>
 *       {/* ... */}
 *     </div>
 *   );
 * }
 * ```
 */
export function usePagination(options: PaginationOptions = {}): PaginationState {
  const { initialPage = 1, pageSize: initialPageSize = 10, totalItems: initialTotalItems = 0 } = options;

  const [currentPage, setCurrentPage] = useState(initialPage);
  const [pageSize, setPageSize] = useState(initialPageSize);
  const [totalItems, setTotalItems] = useState(initialTotalItems);

  // Calculate total pages
  const totalPages = useMemo(() => {
    return Math.max(1, Math.ceil(totalItems / pageSize));
  }, [totalItems, pageSize]);

  // Ensure current page is within valid range
  const validCurrentPage = useMemo(() => {
    return Math.max(1, Math.min(currentPage, totalPages));
  }, [currentPage, totalPages]);

  // Calculate start and end indices (0-indexed)
  const startIndex = useMemo(() => {
    return (validCurrentPage - 1) * pageSize;
  }, [validCurrentPage, pageSize]);

  const endIndex = useMemo(() => {
    return Math.min(startIndex + pageSize - 1, totalItems - 1);
  }, [startIndex, pageSize, totalItems]);

  // Check if there are previous/next pages
  const hasPreviousPage = validCurrentPage > 1;
  const hasNextPage = validCurrentPage < totalPages;

  // Navigation functions
  const goToPage = useCallback(
    (page: number) => {
      const targetPage = Math.max(1, Math.min(page, totalPages));
      setCurrentPage(targetPage);
    },
    [totalPages]
  );

  const nextPage = useCallback(() => {
    if (hasNextPage) {
      setCurrentPage((prev) => prev + 1);
    }
  }, [hasNextPage]);

  const previousPage = useCallback(() => {
    if (hasPreviousPage) {
      setCurrentPage((prev) => prev - 1);
    }
  }, [hasPreviousPage]);

  const firstPage = useCallback(() => {
    setCurrentPage(1);
  }, []);

  const lastPage = useCallback(() => {
    setCurrentPage(totalPages);
  }, [totalPages]);

  const updatePageSize = useCallback((size: number) => {
    const newSize = Math.max(1, size);
    setPageSize(newSize);
    // Reset to first page when page size changes
    setCurrentPage(1);
  }, []);

  const updateTotalItems = useCallback((total: number) => {
    setTotalItems(Math.max(0, total));
  }, []);

  const reset = useCallback(() => {
    setCurrentPage(initialPage);
    setPageSize(initialPageSize);
    setTotalItems(initialTotalItems);
  }, [initialPage, initialPageSize, initialTotalItems]);

  return {
    currentPage: validCurrentPage,
    pageSize,
    totalPages,
    totalItems,
    startIndex,
    endIndex,
    hasPreviousPage,
    hasNextPage,
    goToPage,
    nextPage,
    previousPage,
    firstPage,
    lastPage,
    setPageSize: updatePageSize,
    setTotalItems: updateTotalItems,
    reset,
  };
}

/**
 * Generate an array of page numbers for pagination UI
 *
 * Useful for rendering page number buttons with ellipsis for large page counts
 *
 * @param currentPage - Current page number (1-indexed)
 * @param totalPages - Total number of pages
 * @param maxVisible - Maximum number of page buttons to show (default: 7)
 * @returns Array of page numbers and ellipsis markers
 *
 * @example
 * ```tsx
 * function PaginationControls({ pagination }: { pagination: PaginationState }) {
 *   const pages = getPageNumbers(
 *     pagination.currentPage,
 *     pagination.totalPages,
 *     7
 *   );
 *
 *   return (
 *     <div>
 *       {pages.map((page, index) => {
 *         if (page === '...') {
 *           return <span key={`ellipsis-${index}`}>...</span>;
 *         }
 *         return (
 *           <button
 *             key={page}
 *             onClick={() => pagination.goToPage(page as number)}
 *             disabled={page === pagination.currentPage}
 *           >
 *             {page}
 *           </button>
 *         );
 *       })}
 *     </div>
 *   );
 * }
 * ```
 */
export function getPageNumbers(
  currentPage: number,
  totalPages: number,
  maxVisible: number = 7
): (number | '...')[] {
  if (totalPages <= maxVisible) {
    return Array.from({ length: totalPages }, (_, i) => i + 1);
  }

  const pages: (number | '...')[] = [];
  const halfVisible = Math.floor((maxVisible - 3) / 2); // Account for first, last, and ellipsis

  // Always show first page
  pages.push(1);

  if (currentPage <= halfVisible + 2) {
    // Near the start
    for (let i = 2; i <= maxVisible - 2; i++) {
      pages.push(i);
    }
    pages.push('...');
  } else if (currentPage >= totalPages - halfVisible - 1) {
    // Near the end
    pages.push('...');
    for (let i = totalPages - (maxVisible - 3); i < totalPages; i++) {
      pages.push(i);
    }
  } else {
    // In the middle
    pages.push('...');
    for (let i = currentPage - halfVisible; i <= currentPage + halfVisible; i++) {
      pages.push(i);
    }
    pages.push('...');
  }

  // Always show last page
  pages.push(totalPages);

  return pages;
}
