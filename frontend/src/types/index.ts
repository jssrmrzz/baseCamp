// Business configuration types
export type BusinessType = 'automotive' | 'medspa' | 'consulting' | 'general';
export type ThemeMode = 'light' | 'dark' | 'auto';

export interface BusinessConfig {
  id: string;
  name: string;
  logoUrl?: string;
  businessType: BusinessType;
  theme: ThemeMode;
  primaryColor: string;
  description?: string;
}

// Form data types
export interface ContactInfo {
  name: string;
  email?: string;
  phone?: string;
}

export interface LeadFormData {
  message: string;
  contact: ContactInfo;
  businessId: string;
  source: string;
}

// API response types
export interface LeadSubmissionResponse {
  success: boolean;
  id?: string;
  message?: string;
  error?: string;
}

export interface APIError {
  message: string;
  status?: number;
  details?: string;
}

// Form validation types
export interface FormErrors {
  [key: string]: string | undefined;
}

export interface FormState {
  isSubmitting: boolean;
  isSubmitted: boolean;
  errors: FormErrors;
}

// QR Code types
export interface QRCodeConfig {
  businessId: string;
  source?: string;
  size?: number;
  includeText?: boolean;
}

// Theme types
export interface ThemeColors {
  primary: string;
  secondary: string;
  accent: string;
  background: string;
  text: string;
}