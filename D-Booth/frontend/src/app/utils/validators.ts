/**
 * Frontend validation utilities for D-Booth
 *
 * Provides validation functions and error messages for common form inputs
 */

/**
 * Validation result
 */
export interface ValidationResult {
  /** Whether the value is valid */
  valid: boolean;
  /** Error message if invalid */
  message?: string;
}

/**
 * Email validation
 *
 * @param email - Email address to validate
 * @returns Validation result
 *
 * @example
 * ```ts
 * validateEmail('user@example.com')
 * // => { valid: true }
 *
 * validateEmail('invalid-email')
 * // => { valid: false, message: '请输入有效的邮箱地址' }
 * ```
 */
export function validateEmail(email: string): ValidationResult {
  if (!email || !email.trim()) {
    return { valid: false, message: '邮箱地址不能为空' };
  }

  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  if (!emailRegex.test(email)) {
    return { valid: false, message: '请输入有效的邮箱地址' };
  }

  return { valid: true };
}

/**
 * Phone number validation (supports Chinese mobile numbers)
 *
 * @param phone - Phone number to validate
 * @param allowInternational - Whether to allow international format (default: true)
 * @returns Validation result
 *
 * @example
 * ```ts
 * validatePhone('13812345678')
 * // => { valid: true }
 *
 * validatePhone('+86 138 1234 5678')
 * // => { valid: true }
 *
 * validatePhone('12345')
 * // => { valid: false, message: '请输入有效的手机号码' }
 * ```
 */
export function validatePhone(phone: string, allowInternational: boolean = true): ValidationResult {
  if (!phone || !phone.trim()) {
    return { valid: false, message: '手机号码不能为空' };
  }

  // Remove spaces, dashes, and parentheses
  const cleaned = phone.replace(/[\s\-\(\)]/g, '');

  // Chinese mobile number (11 digits starting with 1)
  const chineseRegex = /^1[3-9]\d{9}$/;

  // International format (+ followed by country code and number)
  const internationalRegex = /^\+\d{1,3}\d{6,14}$/;

  if (allowInternational && cleaned.startsWith('+')) {
    if (!internationalRegex.test(cleaned)) {
      return { valid: false, message: '请输入有效的国际手机号码' };
    }
  } else {
    if (!chineseRegex.test(cleaned)) {
      return { valid: false, message: '请输入有效的手机号码（11位数字）' };
    }
  }

  return { valid: true };
}

/**
 * Password strength validation
 *
 * @param password - Password to validate
 * @param minLength - Minimum password length (default: 8)
 * @param requireSpecialChar - Whether special characters are required (default: true)
 * @returns Validation result
 *
 * @example
 * ```ts
 * validatePassword('weak')
 * // => { valid: false, message: '密码长度至少为8位' }
 *
 * validatePassword('StrongPass123!')
 * // => { valid: true }
 * ```
 */
export function validatePassword(
  password: string,
  minLength: number = 8,
  requireSpecialChar: boolean = true
): ValidationResult {
  if (!password) {
    return { valid: false, message: '密码不能为空' };
  }

  if (password.length < minLength) {
    return { valid: false, message: `密码长度至少为${minLength}位` };
  }

  const hasUpperCase = /[A-Z]/.test(password);
  const hasLowerCase = /[a-z]/.test(password);
  const hasNumber = /\d/.test(password);
  const hasSpecialChar = /[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]/.test(password);

  if (!hasUpperCase || !hasLowerCase) {
    return { valid: false, message: '密码必须包含大小写字母' };
  }

  if (!hasNumber) {
    return { valid: false, message: '密码必须包含数字' };
  }

  if (requireSpecialChar && !hasSpecialChar) {
    return { valid: false, message: '密码必须包含特殊字符' };
  }

  return { valid: true };
}

/**
 * Username validation
 *
 * @param username - Username to validate
 * @param minLength - Minimum username length (default: 3)
 * @param maxLength - Maximum username length (default: 20)
 * @returns Validation result
 *
 * @example
 * ```ts
 * validateUsername('user123')
 * // => { valid: true }
 *
 * validateUsername('u')
 * // => { valid: false, message: '用户名长度为3-20个字符' }
 * ```
 */
export function validateUsername(
  username: string,
  minLength: number = 3,
  maxLength: number = 20
): ValidationResult {
  if (!username || !username.trim()) {
    return { valid: false, message: '用户名不能为空' };
  }

  if (username.length < minLength || username.length > maxLength) {
    return { valid: false, message: `用户名长度为${minLength}-${maxLength}个字符` };
  }

  // Only allow letters, numbers, underscores, and hyphens
  const usernameRegex = /^[a-zA-Z0-9_-]+$/;
  if (!usernameRegex.test(username)) {
    return { valid: false, message: '用户名只能包含字母、数字、下划线和连字符' };
  }

  return { valid: true };
}

/**
 * URL validation
 *
 * @param url - URL to validate
 * @param requireProtocol - Whether protocol (http/https) is required (default: true)
 * @returns Validation result
 *
 * @example
 * ```ts
 * validateUrl('https://example.com')
 * // => { valid: true }
 *
 * validateUrl('example.com', false)
 * // => { valid: true }
 *
 * validateUrl('not a url')
 * // => { valid: false, message: '请输入有效的URL地址' }
 * ```
 */
export function validateUrl(url: string, requireProtocol: boolean = true): ValidationResult {
  if (!url || !url.trim()) {
    return { valid: false, message: 'URL不能为空' };
  }

  try {
    const urlObj = new URL(url);
    if (requireProtocol && !['http:', 'https:'].includes(urlObj.protocol)) {
      return { valid: false, message: 'URL必须以http://或https://开头' };
    }
    return { valid: true };
  } catch {
    if (!requireProtocol) {
      // Try with protocol added
      try {
        new URL(`https://${url}`);
        return { valid: true };
      } catch {
        return { valid: false, message: '请输入有效的URL地址' };
      }
    }
    return { valid: false, message: '请输入有效的URL地址' };
  }
}

/**
 * Required field validation
 *
 * @param value - Value to validate
 * @param fieldName - Name of the field for error message
 * @returns Validation result
 *
 * @example
 * ```ts
 * validateRequired('hello', '用户名')
 * // => { valid: true }
 *
 * validateRequired('', '用户名')
 * // => { valid: false, message: '用户名不能为空' }
 * ```
 */
export function validateRequired(value: any, fieldName: string = '此字段'): ValidationResult {
  if (value === null || value === undefined) {
    return { valid: false, message: `${fieldName}不能为空` };
  }

  if (typeof value === 'string' && !value.trim()) {
    return { valid: false, message: `${fieldName}不能为空` };
  }

  if (Array.isArray(value) && value.length === 0) {
    return { valid: false, message: `${fieldName}不能为空` };
  }

  return { valid: true };
}

/**
 * Number range validation
 *
 * @param value - Number to validate
 * @param min - Minimum value (inclusive)
 * @param max - Maximum value (inclusive)
 * @param fieldName - Name of the field for error message
 * @returns Validation result
 *
 * @example
 * ```ts
 * validateNumberRange(50, 0, 100)
 * // => { valid: true }
 *
 * validateNumberRange(150, 0, 100)
 * // => { valid: false, message: '数值必须在0到100之间' }
 * ```
 */
export function validateNumberRange(
  value: number,
  min: number,
  max: number,
  fieldName: string = '数值'
): ValidationResult {
  if (typeof value !== 'number' || isNaN(value)) {
    return { valid: false, message: `${fieldName}必须是有效的数字` };
  }

  if (value < min || value > max) {
    return { valid: false, message: `${fieldName}必须在${min}到${max}之间` };
  }

  return { valid: true };
}

/**
 * String length validation
 *
 * @param value - String to validate
 * @param minLength - Minimum length
 * @param maxLength - Maximum length
 * @param fieldName - Name of the field for error message
 * @returns Validation result
 *
 * @example
 * ```ts
 * validateLength('hello', 3, 10)
 * // => { valid: true }
 *
 * validateLength('hi', 3, 10)
 * // => { valid: false, message: '长度必须在3到10个字符之间' }
 * ```
 */
export function validateLength(
  value: string,
  minLength: number,
  maxLength: number,
  fieldName: string = '内容'
): ValidationResult {
  if (typeof value !== 'string') {
    return { valid: false, message: `${fieldName}必须是文本` };
  }

  if (value.length < minLength || value.length > maxLength) {
    return { valid: false, message: `${fieldName}长度必须在${minLength}到${maxLength}个字符之间` };
  }

  return { valid: true };
}

/**
 * File validation
 *
 * @param file - File to validate
 * @param options - Validation options
 * @returns Validation result
 *
 * @example
 * ```ts
 * validateFile(imageFile, {
 *   allowedTypes: ['image/jpeg', 'image/png'],
 *   maxSize: 5 * 1024 * 1024, // 5MB
 * })
 * ```
 */
export function validateFile(
  file: File,
  options: {
    allowedTypes?: string[];
    maxSize?: number;
    minSize?: number;
  } = {}
): ValidationResult {
  const { allowedTypes, maxSize, minSize } = options;

  if (!file) {
    return { valid: false, message: '请选择文件' };
  }

  if (allowedTypes && !allowedTypes.includes(file.type)) {
    const types = allowedTypes.map(t => t.split('/')[1]).join('、');
    return { valid: false, message: `文件类型必须是${types}` };
  }

  if (maxSize && file.size > maxSize) {
    const maxSizeMB = (maxSize / (1024 * 1024)).toFixed(1);
    return { valid: false, message: `文件大小不能超过${maxSizeMB}MB` };
  }

  if (minSize && file.size < minSize) {
    const minSizeKB = (minSize / 1024).toFixed(1);
    return { valid: false, message: `文件大小不能小于${minSizeKB}KB` };
  }

  return { valid: true };
}

/**
 * Image dimensions validation
 *
 * @param file - Image file to validate
 * @param options - Validation options
 * @returns Promise resolving to validation result
 *
 * @example
 * ```ts
 * const result = await validateImageDimensions(imageFile, {
 *   minWidth: 800,
 *   minHeight: 600,
 *   maxWidth: 3840,
 *   maxHeight: 2160,
 * });
 * ```
 */
export async function validateImageDimensions(
  file: File,
  options: {
    minWidth?: number;
    minHeight?: number;
    maxWidth?: number;
    maxHeight?: number;
    aspectRatio?: number;
    aspectRatioTolerance?: number;
  } = {}
): Promise<ValidationResult> {
  const { minWidth, minHeight, maxWidth, maxHeight, aspectRatio, aspectRatioTolerance = 0.01 } = options;

  if (!file.type.startsWith('image/')) {
    return { valid: false, message: '文件必须是图片' };
  }

  return new Promise((resolve) => {
    const img = new Image();
    const url = URL.createObjectURL(file);

    img.onload = () => {
      URL.revokeObjectURL(url);

      if (minWidth && img.width < minWidth) {
        resolve({ valid: false, message: `图片宽度不能小于${minWidth}像素` });
        return;
      }

      if (minHeight && img.height < minHeight) {
        resolve({ valid: false, message: `图片高度不能小于${minHeight}像素` });
        return;
      }

      if (maxWidth && img.width > maxWidth) {
        resolve({ valid: false, message: `图片宽度不能超过${maxWidth}像素` });
        return;
      }

      if (maxHeight && img.height > maxHeight) {
        resolve({ valid: false, message: `图片高度不能超过${maxHeight}像素` });
        return;
      }

      if (aspectRatio) {
        const actualRatio = img.width / img.height;
        if (Math.abs(actualRatio - aspectRatio) > aspectRatioTolerance) {
          resolve({ valid: false, message: `图片宽高比必须为${aspectRatio.toFixed(2)}` });
          return;
        }
      }

      resolve({ valid: true });
    };

    img.onerror = () => {
      URL.revokeObjectURL(url);
      resolve({ valid: false, message: '无法读取图片' });
    };

    img.src = url;
  });
}

/**
 * Date validation
 *
 * @param date - Date to validate
 * @param options - Validation options
 * @returns Validation result
 *
 * @example
 * ```ts
 * validateDate(new Date(), { minDate: new Date('2024-01-01') })
 * // => { valid: true }
 *
 * validateDate(new Date('2020-01-01'), { minDate: new Date('2024-01-01') })
 * // => { valid: false, message: '日期不能早于2024-01-01' }
 * ```
 */
export function validateDate(
  date: Date | string | number,
  options: {
    minDate?: Date | string | number;
    maxDate?: Date | string | number;
    allowFuture?: boolean;
    allowPast?: boolean;
  } = {}
): ValidationResult {
  const { minDate, maxDate, allowFuture = true, allowPast = true } = options;

  const dateObj = typeof date === 'string' || typeof date === 'number' ? new Date(date) : date;

  if (!(dateObj instanceof Date) || isNaN(dateObj.getTime())) {
    return { valid: false, message: '无效的日期' };
  }

  const now = new Date();

  if (!allowFuture && dateObj > now) {
    return { valid: false, message: '日期不能是未来日期' };
  }

  if (!allowPast && dateObj < now) {
    return { valid: false, message: '日期不能是过去日期' };
  }

  if (minDate) {
    const minDateObj = typeof minDate === 'string' || typeof minDate === 'number' ? new Date(minDate) : minDate;
    if (dateObj < minDateObj) {
      return { valid: false, message: `日期不能早于${minDateObj.toLocaleDateString('zh-CN')}` };
    }
  }

  if (maxDate) {
    const maxDateObj = typeof maxDate === 'string' || typeof maxDate === 'number' ? new Date(maxDate) : maxDate;
    if (dateObj > maxDateObj) {
      return { valid: false, message: `日期不能晚于${maxDateObj.toLocaleDateString('zh-CN')}` };
    }
  }

  return { valid: true };
}

/**
 * Chinese ID card validation (身份证号码验证)
 *
 * @param idCard - ID card number to validate
 * @returns Validation result
 *
 * @example
 * ```ts
 * validateChineseIdCard('11010519491231002X')
 * // => { valid: true }
 * ```
 */
export function validateChineseIdCard(idCard: string): ValidationResult {
  if (!idCard || !idCard.trim()) {
    return { valid: false, message: '身份证号码不能为空' };
  }

  const cleaned = idCard.trim().toUpperCase();

  // Must be 18 digits
  if (!/^\d{17}[\dX]$/.test(cleaned)) {
    return { valid: false, message: '身份证号码格式不正确' };
  }

  // Validate checksum
  const factors = [7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2];
  const checksumChars = '10X98765432';

  let sum = 0;
  for (let i = 0; i < 17; i++) {
    sum += parseInt(cleaned[i]) * factors[i];
  }

  const expectedChecksum = checksumChars[sum % 11];
  const actualChecksum = cleaned[17];

  if (expectedChecksum !== actualChecksum) {
    return { valid: false, message: '身份证号码校验失败' };
  }

  return { valid: true };
}

/**
 * Compose multiple validators
 *
 * @param validators - Array of validator functions
 * @returns Combined validator function
 *
 * @example
 * ```ts
 * const validateUserEmail = composeValidators([
 *   (value) => validateRequired(value, '邮箱'),
 *   validateEmail,
 * ]);
 *
 * const result = validateUserEmail('user@example.com');
 * ```
 */
export function composeValidators(
  validators: Array<(value: any) => ValidationResult>
): (value: any) => ValidationResult {
  return (value: any): ValidationResult => {
    for (const validator of validators) {
      const result = validator(value);
      if (!result.valid) {
        return result;
      }
    }
    return { valid: true };
  };
}
