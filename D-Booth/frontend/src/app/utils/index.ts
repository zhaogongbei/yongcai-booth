/**
 * Utility Functions and Validators for D-Booth
 *
 * Re-exports all utility functions and validators
 */

// Utilities
export {
  formatDate,
  formatDateTime,
  formatRelativeTime,
  formatFileSize,
  formatNumber,
  formatCurrency,
  truncate,
  capitalize,
  generateId,
  sleep,
  deepClone,
  isEqual,
  debounce,
  throttle,
  groupBy,
  pick,
  omit,
  isEmpty,
  clamp,
  getNestedValue,
  downloadFile,
  copyToClipboard,
} from './utils';

// Validators
export {
  validateEmail,
  validatePhone,
  validatePassword,
  validateUsername,
  validateUrl,
  validateRequired,
  validateNumberRange,
  validateLength,
  validateFile,
  validateImageDimensions,
  validateDate,
  validateChineseIdCard,
  composeValidators,
} from './validators';

export type { ValidationResult } from './validators';
