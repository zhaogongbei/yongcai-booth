/**
 * Common utility functions for D-Booth frontend
 */

/**
 * Format a date to a localized string
 *
 * @param date - Date to format
 * @param locale - Locale string (default: 'zh-CN')
 * @param options - Intl.DateTimeFormatOptions
 * @returns Formatted date string
 *
 * @example
 * ```ts
 * formatDate(new Date())
 * // => "2024年7月2日"
 *
 * formatDate(new Date(), 'en-US', { dateStyle: 'medium' })
 * // => "Jul 2, 2024"
 * ```
 */
export function formatDate(
  date: Date | string | number,
  locale: string = 'zh-CN',
  options: Intl.DateTimeFormatOptions = { dateStyle: 'medium' }
): string {
  const dateObj = typeof date === 'string' || typeof date === 'number' ? new Date(date) : date;
  return new Intl.DateTimeFormat(locale, options).format(dateObj);
}

/**
 * Format a date and time to a localized string
 *
 * @param date - Date to format
 * @param locale - Locale string (default: 'zh-CN')
 * @returns Formatted datetime string
 *
 * @example
 * ```ts
 * formatDateTime(new Date())
 * // => "2024年7月2日 下午3:45"
 * ```
 */
export function formatDateTime(
  date: Date | string | number,
  locale: string = 'zh-CN'
): string {
  return formatDate(date, locale, { dateStyle: 'medium', timeStyle: 'short' });
}

/**
 * Format a relative time string (e.g., "2 hours ago")
 *
 * @param date - Date to format
 * @param locale - Locale string (default: 'zh-CN')
 * @returns Relative time string
 *
 * @example
 * ```ts
 * formatRelativeTime(Date.now() - 3600000) // 1 hour ago
 * // => "1小时前"
 *
 * formatRelativeTime(Date.now() + 86400000) // 1 day from now
 * // => "1天后"
 * ```
 */
export function formatRelativeTime(
  date: Date | string | number,
  locale: string = 'zh-CN'
): string {
  const dateObj = typeof date === 'string' || typeof date === 'number' ? new Date(date) : date;
  const now = new Date();
  const diffMs = dateObj.getTime() - now.getTime();
  const diffSec = Math.round(diffMs / 1000);
  const diffMin = Math.round(diffSec / 60);
  const diffHour = Math.round(diffMin / 60);
  const diffDay = Math.round(diffHour / 24);

  const rtf = new Intl.RelativeTimeFormat(locale, { numeric: 'auto' });

  if (Math.abs(diffSec) < 60) {
    return rtf.format(diffSec, 'second');
  } else if (Math.abs(diffMin) < 60) {
    return rtf.format(diffMin, 'minute');
  } else if (Math.abs(diffHour) < 24) {
    return rtf.format(diffHour, 'hour');
  } else if (Math.abs(diffDay) < 30) {
    return rtf.format(diffDay, 'day');
  } else {
    return formatDate(dateObj, locale);
  }
}

/**
 * Format file size to human-readable string
 *
 * @param bytes - File size in bytes
 * @param decimals - Number of decimal places (default: 2)
 * @returns Formatted file size string
 *
 * @example
 * ```ts
 * formatFileSize(1024)
 * // => "1.00 KB"
 *
 * formatFileSize(1536000)
 * // => "1.46 MB"
 * ```
 */
export function formatFileSize(bytes: number, decimals: number = 2): string {
  if (bytes === 0) return '0 Bytes';

  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB', 'PB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));

  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(decimals))} ${sizes[i]}`;
}

/**
 * Format a number with thousands separators
 *
 * @param value - Number to format
 * @param locale - Locale string (default: 'zh-CN')
 * @returns Formatted number string
 *
 * @example
 * ```ts
 * formatNumber(1234567.89)
 * // => "1,234,567.89"
 * ```
 */
export function formatNumber(value: number, locale: string = 'zh-CN'): string {
  return new Intl.NumberFormat(locale).format(value);
}

/**
 * Format currency amount
 *
 * @param amount - Amount to format
 * @param currency - Currency code (default: 'CNY')
 * @param locale - Locale string (default: 'zh-CN')
 * @returns Formatted currency string
 *
 * @example
 * ```ts
 * formatCurrency(1234.56)
 * // => "¥1,234.56"
 *
 * formatCurrency(1234.56, 'USD', 'en-US')
 * // => "$1,234.56"
 * ```
 */
export function formatCurrency(
  amount: number,
  currency: string = 'CNY',
  locale: string = 'zh-CN'
): string {
  return new Intl.NumberFormat(locale, {
    style: 'currency',
    currency,
  }).format(amount);
}

/**
 * Truncate a string to a maximum length with ellipsis
 *
 * @param str - String to truncate
 * @param maxLength - Maximum length (default: 50)
 * @param suffix - Suffix to add when truncated (default: '...')
 * @returns Truncated string
 *
 * @example
 * ```ts
 * truncate('This is a very long string', 10)
 * // => "This is a..."
 * ```
 */
export function truncate(str: string, maxLength: number = 50, suffix: string = '...'): string {
  if (str.length <= maxLength) return str;
  return str.slice(0, maxLength - suffix.length) + suffix;
}

/**
 * Capitalize the first letter of a string
 *
 * @param str - String to capitalize
 * @returns Capitalized string
 *
 * @example
 * ```ts
 * capitalize('hello world')
 * // => "Hello world"
 * ```
 */
export function capitalize(str: string): string {
  if (!str) return str;
  return str.charAt(0).toUpperCase() + str.slice(1);
}

/**
 * Generate a random ID string
 *
 * @param length - Length of the ID (default: 8)
 * @returns Random ID string
 *
 * @example
 * ```ts
 * generateId()
 * // => "a3f9d2c1"
 *
 * generateId(16)
 * // => "a3f9d2c1b7e4f6a8"
 * ```
 */
export function generateId(length: number = 8): string {
  const chars = 'abcdefghijklmnopqrstuvwxyz0123456789';
  let result = '';
  for (let i = 0; i < length; i++) {
    result += chars.charAt(Math.floor(Math.random() * chars.length));
  }
  return result;
}

/**
 * Sleep for a specified duration
 *
 * @param ms - Duration in milliseconds
 * @returns Promise that resolves after the duration
 *
 * @example
 * ```ts
 * await sleep(1000); // Wait 1 second
 * console.log('Done');
 * ```
 */
export function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/**
 * Deep clone an object
 *
 * @param obj - Object to clone
 * @returns Cloned object
 *
 * @example
 * ```ts
 * const original = { a: 1, b: { c: 2 } };
 * const cloned = deepClone(original);
 * cloned.b.c = 3;
 * console.log(original.b.c); // => 2
 * ```
 */
export function deepClone<T>(obj: T): T {
  if (obj === null || typeof obj !== 'object') return obj;
  if (obj instanceof Date) return new Date(obj.getTime()) as unknown as T;
  if (obj instanceof Array) return obj.map((item) => deepClone(item)) as unknown as T;
  if (obj instanceof Object) {
    const clonedObj: Record<string, unknown> = {};
    for (const key in obj) {
      if (Object.prototype.hasOwnProperty.call(obj, key)) {
        clonedObj[key] = deepClone(obj[key]);
      }
    }
    return clonedObj as T;
  }
  return obj;
}

/**
 * Check if two objects are deeply equal
 *
 * @param a - First object
 * @param b - Second object
 * @returns True if objects are deeply equal
 *
 * @example
 * ```ts
 * isEqual({ a: 1, b: { c: 2 } }, { a: 1, b: { c: 2 } })
 * // => true
 * ```
 */
export function isEqual(a: unknown, b: unknown): boolean {
  if (a === b) return true;
  if (a == null || b == null) return false;
  if (typeof a !== 'object' || typeof b !== 'object') return false;

  const keysA = Object.keys(a as object);
  const keysB = Object.keys(b as object);

  if (keysA.length !== keysB.length) return false;

  for (const key of keysA) {
    if (!keysB.includes(key)) return false;
    if (!isEqual((a as Record<string, unknown>)[key], (b as Record<string, unknown>)[key])) {
      return false;
    }
  }

  return true;
}

/**
 * Debounce a function
 *
 * @param fn - Function to debounce
 * @param delay - Delay in milliseconds
 * @returns Debounced function
 *
 * @example
 * ```ts
 * const search = debounce((query: string) => {
 *   console.log('Searching for:', query);
 * }, 300);
 *
 * search('hello');
 * search('hello world'); // Only this will execute after 300ms
 * ```
 */
export function debounce<T extends (...args: any[]) => any>(
  fn: T,
  delay: number
): (...args: Parameters<T>) => void {
  let timeoutId: NodeJS.Timeout | null = null;

  return function (...args: Parameters<T>) {
    if (timeoutId) clearTimeout(timeoutId);
    timeoutId = setTimeout(() => fn(...args), delay);
  };
}

/**
 * Throttle a function
 *
 * @param fn - Function to throttle
 * @param limit - Minimum time between executions in milliseconds
 * @returns Throttled function
 *
 * @example
 * ```ts
 * const handleScroll = throttle(() => {
 *   console.log('Scrolled');
 * }, 200);
 *
 * window.addEventListener('scroll', handleScroll);
 * ```
 */
export function throttle<T extends (...args: any[]) => any>(
  fn: T,
  limit: number
): (...args: Parameters<T>) => void {
  let inThrottle = false;

  return function (...args: Parameters<T>) {
    if (!inThrottle) {
      fn(...args);
      inThrottle = true;
      setTimeout(() => {
        inThrottle = false;
      }, limit);
    }
  };
}

/**
 * Group an array of objects by a key
 *
 * @param array - Array to group
 * @param key - Key to group by
 * @returns Object with grouped arrays
 *
 * @example
 * ```ts
 * const users = [
 *   { name: 'Alice', role: 'admin' },
 *   { name: 'Bob', role: 'user' },
 *   { name: 'Charlie', role: 'admin' },
 * ];
 *
 * groupBy(users, 'role')
 * // => {
 * //   admin: [{ name: 'Alice', role: 'admin' }, { name: 'Charlie', role: 'admin' }],
 * //   user: [{ name: 'Bob', role: 'user' }]
 * // }
 * ```
 */
export function groupBy<T extends Record<string, any>>(
  array: T[],
  key: keyof T
): Record<string, T[]> {
  return array.reduce(
    (result, item) => {
      const groupKey = String(item[key]);
      if (!result[groupKey]) {
        result[groupKey] = [];
      }
      result[groupKey].push(item);
      return result;
    },
    {} as Record<string, T[]>
  );
}

/**
 * Pick specific keys from an object
 *
 * @param obj - Object to pick from
 * @param keys - Keys to pick
 * @returns New object with only the picked keys
 *
 * @example
 * ```ts
 * const user = { id: 1, name: 'Alice', email: 'alice@example.com', password: 'secret' };
 * pick(user, ['id', 'name'])
 * // => { id: 1, name: 'Alice' }
 * ```
 */
export function pick<T extends Record<string, any>, K extends keyof T>(
  obj: T,
  keys: K[]
): Pick<T, K> {
  const result = {} as Pick<T, K>;
  for (const key of keys) {
    if (key in obj) {
      result[key] = obj[key];
    }
  }
  return result;
}

/**
 * Omit specific keys from an object
 *
 * @param obj - Object to omit from
 * @param keys - Keys to omit
 * @returns New object without the omitted keys
 *
 * @example
 * ```ts
 * const user = { id: 1, name: 'Alice', email: 'alice@example.com', password: 'secret' };
 * omit(user, ['password'])
 * // => { id: 1, name: 'Alice', email: 'alice@example.com' }
 * ```
 */
export function omit<T extends Record<string, any>, K extends keyof T>(
  obj: T,
  keys: K[]
): Omit<T, K> {
  const result = { ...obj };
  for (const key of keys) {
    delete result[key];
  }
  return result;
}

/**
 * Check if a value is empty (null, undefined, empty string, empty array, empty object)
 *
 * @param value - Value to check
 * @returns True if value is empty
 *
 * @example
 * ```ts
 * isEmpty(null) // => true
 * isEmpty('') // => true
 * isEmpty([]) // => true
 * isEmpty({}) // => true
 * isEmpty('hello') // => false
 * isEmpty([1, 2]) // => false
 * ```
 */
export function isEmpty(value: unknown): boolean {
  if (value == null) return true;
  if (typeof value === 'string') return value.trim().length === 0;
  if (Array.isArray(value)) return value.length === 0;
  if (typeof value === 'object') return Object.keys(value).length === 0;
  return false;
}

/**
 * Clamp a number between min and max values
 *
 * @param value - Value to clamp
 * @param min - Minimum value
 * @param max - Maximum value
 * @returns Clamped value
 *
 * @example
 * ```ts
 * clamp(5, 0, 10) // => 5
 * clamp(-5, 0, 10) // => 0
 * clamp(15, 0, 10) // => 10
 * ```
 */
export function clamp(value: number, min: number, max: number): number {
  return Math.min(Math.max(value, min), max);
}

/**
 * Get a nested property from an object using dot notation
 *
 * @param obj - Object to get property from
 * @param path - Property path (e.g., 'user.profile.name')
 * @param defaultValue - Default value if property doesn't exist
 * @returns Property value or default value
 *
 * @example
 * ```ts
 * const data = { user: { profile: { name: 'Alice' } } };
 * getNestedValue(data, 'user.profile.name') // => 'Alice'
 * getNestedValue(data, 'user.settings.theme', 'light') // => 'light'
 * ```
 */
export function getNestedValue<T = any>(
  obj: any,
  path: string,
  defaultValue?: T
): T | undefined {
  const keys = path.split('.');
  let result = obj;

  for (const key of keys) {
    if (result == null || typeof result !== 'object') {
      return defaultValue;
    }
    result = result[key];
  }

  return result !== undefined ? result : defaultValue;
}

/**
 * Download a file from a URL or Blob
 *
 * @param data - URL string or Blob to download
 * @param filename - Name of the downloaded file
 *
 * @example
 * ```ts
 * // Download from URL
 * downloadFile('https://example.com/file.pdf', 'document.pdf');
 *
 * // Download from Blob
 * const blob = new Blob(['Hello, world!'], { type: 'text/plain' });
 * downloadFile(blob, 'hello.txt');
 * ```
 */
export function downloadFile(data: string | Blob, filename: string): void {
  const url = typeof data === 'string' ? data : URL.createObjectURL(data);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);

  // Clean up blob URL
  if (typeof data !== 'string') {
    URL.revokeObjectURL(url);
  }
}

/**
 * Copy text to clipboard
 *
 * @param text - Text to copy
 * @returns Promise that resolves when text is copied
 *
 * @example
 * ```ts
 * await copyToClipboard('Hello, world!');
 * console.log('Copied!');
 * ```
 */
export async function copyToClipboard(text: string): Promise<void> {
  if (navigator.clipboard) {
    await navigator.clipboard.writeText(text);
  } else {
    // Fallback for older browsers
    const textarea = document.createElement('textarea');
    textarea.value = text;
    textarea.style.position = 'fixed';
    textarea.style.opacity = '0';
    document.body.appendChild(textarea);
    textarea.select();
    document.execCommand('copy');
    document.body.removeChild(textarea);
  }
}
