import { z } from 'zod';
import type { LeadFormData, FormErrors } from '../types';

// Zod schema for form validation
export const leadFormSchema = z.object({
  message: z
    .string()
    .min(10, 'Please provide at least 10 characters describing your need')
    .max(1000, 'Message is too long (maximum 1000 characters)'),
  
  contact: z.object({
    name: z
      .string()
      .min(2, 'Name must be at least 2 characters')
      .max(100, 'Name is too long'),
    
    email: z
      .string()
      .email('Please enter a valid email address')
      .optional()
      .or(z.literal('')),
    
    phone: z
      .string()
      .regex(/^[\d\s\-\+\(\)\.]{10,}$/, 'Please enter a valid phone number')
      .optional()
      .or(z.literal('')),
  }),
  
  businessId: z.string().min(1, 'Business ID is required'),
  source: z.string().min(1, 'Source is required'),
});

// Type for form data
export type LeadFormInput = z.infer<typeof leadFormSchema>;

/**
 * Validate form data and return errors
 */
export function validateLeadForm(data: Partial<LeadFormData>): FormErrors {
  try {
    leadFormSchema.parse(data);
    return {};
  } catch (error) {
    if (error instanceof z.ZodError) {
      const errors: FormErrors = {};
      
      error.issues.forEach((err: z.ZodIssue) => {
        const path = err.path.join('.');
        errors[path] = err.message;
      });
      
      return errors;
    }
    
    return { general: 'Validation failed' };
  }
}

/**
 * Validate individual field
 */
export function validateField(
  fieldName: keyof LeadFormData | string,
  _value: any,
  data: Partial<LeadFormData>
): string | undefined {
  const errors = validateLeadForm(data);
  return errors[fieldName];
}

/**
 * Check if at least one contact method is provided
 */
export function validateContactInfo(contact: { email?: string; phone?: string }): string | undefined {
  const hasEmail = contact.email && contact.email.trim().length > 0;
  const hasPhone = contact.phone && contact.phone.trim().length > 0;
  
  if (!hasEmail && !hasPhone) {
    return 'Please provide either an email address or phone number so we can contact you';
  }
  
  return undefined;
}

/**
 * Format phone number for display
 */
export function formatPhoneNumber(phone: string): string {
  // Remove all non-digit characters
  const digits = phone.replace(/\D/g, '');
  
  // Format US phone numbers
  if (digits.length === 10) {
    return `(${digits.slice(0, 3)}) ${digits.slice(3, 6)}-${digits.slice(6)}`;
  }
  
  if (digits.length === 11 && digits.startsWith('1')) {
    return `+1 (${digits.slice(1, 4)}) ${digits.slice(4, 7)}-${digits.slice(7)}`;
  }
  
  // Return original if we can't format
  return phone;
}