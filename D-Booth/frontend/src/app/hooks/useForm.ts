import { useState, useCallback, useRef, useEffect } from 'react';

/**
 * Form field validation function
 */
export type Validator<T> = (value: T) => string | null | Promise<string | null>;

/**
 * Form field configuration
 */
export interface FieldConfig<T = any> {
  /** Initial value */
  initialValue: T;
  /** Validation function or array of validation functions */
  validate?: Validator<T> | Validator<T>[];
  /** Whether to validate on change (default: false) */
  validateOnChange?: boolean;
  /** Whether to validate on blur (default: true) */
  validateOnBlur?: boolean;
}

/**
 * Form configuration
 */
export interface FormConfig<T extends Record<string, any>> {
  /** Initial form values */
  initialValues: T;
  /** Field configurations */
  fields?: Partial<Record<keyof T, Omit<FieldConfig, 'initialValue'>>>;
  /** Form-level validation */
  validate?: (values: T) => Partial<Record<keyof T, string>> | Promise<Partial<Record<keyof T, string>>>;
  /** Callback on successful submission */
  onSubmit?: (values: T) => void | Promise<void>;
}

/**
 * Field state
 */
export interface FieldState<T = any> {
  value: T;
  error: string | null;
  touched: boolean;
  dirty: boolean;
}

/**
 * Form state
 */
export interface FormState<T extends Record<string, any>> {
  values: T;
  errors: Partial<Record<keyof T, string>>;
  touched: Partial<Record<keyof T, boolean>>;
  dirty: Partial<Record<keyof T, boolean>>;
  isSubmitting: boolean;
  isValidating: boolean;
  isValid: boolean;
  submitCount: number;
}

/**
 * Form management hook
 *
 * Provides comprehensive form state management with validation, error handling,
 * and field-level tracking. Supports both synchronous and asynchronous validation.
 *
 * @param config - Form configuration
 * @returns Form state and control methods
 *
 * @example
 * ```tsx
 * // Basic usage
 * interface LoginForm {
 *   username: string;
 *   password: string;
 * }
 *
 * function LoginForm() {
 *   const form = useForm<LoginForm>({
 *     initialValues: {
 *       username: '',
 *       password: '',
 *     },
 *     fields: {
 *       username: {
 *         validate: (value) => {
 *           if (!value) return 'Username is required';
 *           if (value.length < 3) return 'Username must be at least 3 characters';
 *           return null;
 *         },
 *       },
 *       password: {
 *         validate: (value) => {
 *           if (!value) return 'Password is required';
 *           if (value.length < 6) return 'Password must be at least 6 characters';
 *           return null;
 *         },
 *       },
 *     },
 *     onSubmit: async (values) => {
 *       await login(values);
 *     },
 *   });
 *
 *   return (
 *     <form onSubmit={form.handleSubmit}>
 *       <input
 *         {...form.getFieldProps('username')}
 *         placeholder="Username"
 *       />
 *       {form.errors.username && form.touched.username && (
 *         <span className="error">{form.errors.username}</span>
 *       )}
 *
 *       <input
 *         {...form.getFieldProps('password')}
 *         type="password"
 *         placeholder="Password"
 *       />
 *       {form.errors.password && form.touched.password && (
 *         <span className="error">{form.errors.password}</span>
 *       )}
 *
 *       <button type="submit" disabled={form.isSubmitting || !form.isValid}>
 *         {form.isSubmitting ? 'Logging in...' : 'Login'}
 *       </button>
 *     </form>
 *   );
 * }
 *
 * // With async validation
 * function SignupForm() {
 *   const form = useForm({
 *     initialValues: { email: '' },
 *     fields: {
 *       email: {
 *         validate: async (value) => {
 *           if (!value) return 'Email is required';
 *           const exists = await checkEmailExists(value);
 *           return exists ? 'Email already taken' : null;
 *         },
 *         validateOnBlur: true,
 *       },
 *     },
 *   });
 *
 *   return <form>...</form>;
 * }
 * ```
 */
export function useForm<T extends Record<string, any>>(
  config: FormConfig<T>
): FormState<T> & {
  setFieldValue: <K extends keyof T>(field: K, value: T[K]) => void;
  setFieldError: <K extends keyof T>(field: K, error: string | null) => void;
  setFieldTouched: <K extends keyof T>(field: K, touched: boolean) => void;
  setValues: (values: Partial<T>) => void;
  setErrors: (errors: Partial<Record<keyof T, string>>) => void;
  resetForm: () => void;
  validateField: <K extends keyof T>(field: K) => Promise<boolean>;
  validateForm: () => Promise<boolean>;
  handleSubmit: (e?: React.FormEvent) => Promise<void>;
  handleChange: (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => void;
  handleBlur: (e: React.FocusEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => void;
  getFieldProps: <K extends keyof T>(field: K) => {
    name: string;
    value: T[K];
    onChange: (e: React.ChangeEvent<any>) => void;
    onBlur: (e: React.FocusEvent<any>) => void;
  };
} {
  const { initialValues, fields = {}, validate, onSubmit } = config;

  const [values, setValuesState] = useState<T>(initialValues);
  const [errors, setErrorsState] = useState<Partial<Record<keyof T, string>>>({});
  const [touched, setTouchedState] = useState<Partial<Record<keyof T, boolean>>>({});
  const [dirty, setDirtyState] = useState<Partial<Record<keyof T, boolean>>>();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isValidating, setIsValidating] = useState(false);
  const [submitCount, setSubmitCount] = useState(0);

  const initialValuesRef = useRef(initialValues);
  const mountedRef = useRef(true);

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
    };
  }, []);

  /**
   * Set a single field value
   */
  const setFieldValue = useCallback(
    <K extends keyof T>(field: K, value: T[K]) => {
      setValuesState((prev) => ({ ...prev, [field]: value }));
      setDirtyState((prev) => ({
        ...prev,
        [field]: value !== initialValuesRef.current[field],
      }));

      // Validate on change if configured
      const fieldConfig = fields[field];
      if (fieldConfig?.validateOnChange) {
        void validateField(field);
      }
    },
    [fields]
  );

  /**
   * Set a single field error
   */
  const setFieldError = useCallback(<K extends keyof T>(field: K, error: string | null) => {
    setErrorsState((prev) => ({
      ...prev,
      [field]: error ?? undefined,
    }));
  }, []);

  /**
   * Set a single field touched state
   */
  const setFieldTouched = useCallback(<K extends keyof T>(field: K, touched: boolean) => {
    setTouchedState((prev) => ({
      ...prev,
      [field]: touched,
    }));
  }, []);

  /**
   * Set multiple values at once
   */
  const setValues = useCallback((newValues: Partial<T>) => {
    setValuesState((prev) => ({ ...prev, ...newValues }));
    setDirtyState((prev) => {
      const newDirty = { ...prev };
      for (const key in newValues) {
        newDirty[key] = newValues[key] !== initialValuesRef.current[key];
      }
      return newDirty;
    });
  }, []);

  /**
   * Set multiple errors at once
   */
  const setErrors = useCallback((newErrors: Partial<Record<keyof T, string>>) => {
    setErrorsState(newErrors);
  }, []);

  /**
   * Reset form to initial state
   */
  const resetForm = useCallback(() => {
    setValuesState(initialValuesRef.current);
    setErrorsState({});
    setTouchedState({});
    setDirtyState({});
    setIsSubmitting(false);
    setIsValidating(false);
    setSubmitCount(0);
  }, []);

  /**
   * Validate a single field
   */
  const validateField = useCallback(
    async <K extends keyof T>(field: K): Promise<boolean> => {
      const fieldConfig = fields[field];
      if (!fieldConfig?.validate) return true;

      const validators = Array.isArray(fieldConfig.validate)
        ? fieldConfig.validate
        : [fieldConfig.validate];

      setIsValidating(true);

      try {
        for (const validator of validators) {
          const error = await validator(values[field]);
          if (error) {
            if (mountedRef.current) {
              setFieldError(field, error);
            }
            return false;
          }
        }

        if (mountedRef.current) {
          setFieldError(field, null);
        }
        return true;
      } catch (err) {
        const error = err instanceof Error ? err.message : 'Validation error';
        if (mountedRef.current) {
          setFieldError(field, error);
        }
        return false;
      } finally {
        if (mountedRef.current) {
          setIsValidating(false);
        }
      }
    },
    [fields, values, setFieldError]
  );

  /**
   * Validate entire form
   */
  const validateForm = useCallback(async (): Promise<boolean> => {
    setIsValidating(true);

    const newErrors: Partial<Record<keyof T, string>> = {};
    let isValid = true;

    // Run field-level validations
    for (const field in fields) {
      const fieldConfig = fields[field];
      if (!fieldConfig?.validate) continue;

      const validators = Array.isArray(fieldConfig.validate)
        ? fieldConfig.validate
        : [fieldConfig.validate];

      for (const validator of validators) {
        try {
          const error = await validator(values[field]);
          if (error) {
            newErrors[field] = error;
            isValid = false;
            break;
          }
        } catch (err) {
          newErrors[field] = err instanceof Error ? err.message : 'Validation error';
          isValid = false;
          break;
        }
      }
    }

    // Run form-level validation
    if (validate) {
      try {
        const formErrors = await validate(values);
        Object.assign(newErrors, formErrors);
        if (Object.keys(formErrors).length > 0) {
          isValid = false;
        }
      } catch (err) {
        console.error('Form validation error:', err);
        isValid = false;
      }
    }

    if (mountedRef.current) {
      setErrorsState(newErrors);
      setIsValidating(false);
    }

    return isValid;
  }, [fields, validate, values]);

  /**
   * Handle form submission
   */
  const handleSubmit = useCallback(
    async (e?: React.FormEvent) => {
      e?.preventDefault();

      setSubmitCount((prev) => prev + 1);
      setIsSubmitting(true);

      // Mark all fields as touched
      const allTouched: Partial<Record<keyof T, boolean>> = {};
      for (const key in values) {
        allTouched[key] = true;
      }
      setTouchedState(allTouched);

      // Validate form
      const isValid = await validateForm();

      if (isValid && onSubmit) {
        try {
          await onSubmit(values);
        } catch (err) {
          console.error('Form submission error:', err);
        }
      }

      if (mountedRef.current) {
        setIsSubmitting(false);
      }
    },
    [values, validateForm, onSubmit]
  );

  /**
   * Handle input change
   */
  const handleChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
      const { name, value, type } = e.target;
      const fieldValue =
        type === 'checkbox' ? (e.target as HTMLInputElement).checked : value;

      setFieldValue(name as keyof T, fieldValue as T[keyof T]);
    },
    [setFieldValue]
  );

  /**
   * Handle input blur
   */
  const handleBlur = useCallback(
    (e: React.FocusEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
      const { name } = e.target;
      const field = name as keyof T;

      setFieldTouched(field, true);

      // Validate on blur if configured
      const fieldConfig = fields[field];
      if (fieldConfig?.validateOnBlur !== false) {
        void validateField(field);
      }
    },
    [fields, setFieldTouched, validateField]
  );

  /**
   * Get props for a field (name, value, onChange, onBlur)
   */
  const getFieldProps = useCallback(
    <K extends keyof T>(field: K) => ({
      name: field as string,
      value: values[field],
      onChange: handleChange,
      onBlur: handleBlur,
    }),
    [values, handleChange, handleBlur]
  );

  // Check if form is valid
  const isValid = Object.keys(errors).length === 0;

  return {
    values,
    errors,
    touched,
    dirty,
    isSubmitting,
    isValidating,
    isValid,
    submitCount,
    setFieldValue,
    setFieldError,
    setFieldTouched,
    setValues,
    setErrors,
    resetForm,
    validateField,
    validateForm,
    handleSubmit,
    handleChange,
    handleBlur,
    getFieldProps,
  };
}
