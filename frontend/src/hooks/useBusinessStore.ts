import { create } from 'zustand';
import type { BusinessConfig, FormState } from '../types';
import { getBusinessConfig } from '../services/businessConfig';
import { applyTheme } from '../services/theme';

interface BusinessStore {
  // Business configuration
  currentBusiness: BusinessConfig | null;
  isBusinessLoading: boolean;
  
  // Form state
  formState: FormState;
  
  // Actions
  setBusinessId: (businessId: string) => void;
  setFormState: (state: Partial<FormState>) => void;
  resetFormState: () => void;
}

const initialFormState: FormState = {
  isSubmitting: false,
  isSubmitted: false,
  errors: {},
};

export const useBusinessStore = create<BusinessStore>((set, get) => ({
  // Initial state
  currentBusiness: null,
  isBusinessLoading: false,
  formState: initialFormState,

  // Actions
  setBusinessId: (businessId: string) => {
    set({ isBusinessLoading: true });
    
    try {
      const businessConfig = getBusinessConfig(businessId);
      
      // Apply theme
      applyTheme(businessConfig);
      
      set({
        currentBusiness: businessConfig,
        isBusinessLoading: false,
      });
    } catch (error) {
      console.error('Failed to load business config:', error);
      set({ isBusinessLoading: false });
    }
  },

  setFormState: (state: Partial<FormState>) => {
    const currentFormState = get().formState;
    set({
      formState: { ...currentFormState, ...state },
    });
  },

  resetFormState: () => {
    set({ formState: initialFormState });
  },
}));