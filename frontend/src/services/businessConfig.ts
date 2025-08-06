import type { BusinessConfig, BusinessType } from '../types';

// Static business configurations for MVP
// In production, these would come from an API or database
const businessConfigs: Record<string, BusinessConfig> = {
  'demo-auto': {
    id: 'demo-auto',
    name: 'Premier Auto Service',
    businessType: 'automotive',
    theme: 'light',
    primaryColor: '#dc2626', // Red for automotive
    description: 'Professional automotive service and repair',
    logoUrl: undefined, // Could be added later
  },
  'demo-medspa': {
    id: 'demo-medspa',
    name: 'Serenity MedSpa',
    businessType: 'medspa',
    theme: 'light',
    primaryColor: '#7c3aed', // Purple for wellness
    description: 'Luxury medical spa and wellness treatments',
  },
  'demo-consulting': {
    id: 'demo-consulting',
    name: 'Strategic Business Solutions',
    businessType: 'consulting',
    theme: 'light',
    primaryColor: '#059669', // Green for business
    description: 'Professional business consulting services',
  },
  'demo-general': {
    id: 'demo-general',
    name: 'Quality Service Co.',
    businessType: 'general',
    theme: 'light',
    primaryColor: '#2563eb', // Blue for general
    description: 'Quality services for your business needs',
  },
};

// Default configuration fallback
const defaultConfig: BusinessConfig = {
  id: 'default',
  name: 'Service Business',
  businessType: 'general',
  theme: 'light',
  primaryColor: '#2563eb',
  description: 'Professional services',
};

/**
 * Get business configuration by ID
 */
export function getBusinessConfig(businessId: string): BusinessConfig {
  const config = businessConfigs[businessId];
  
  if (!config) {
    console.warn(`Business config not found for ID: ${businessId}. Using default.`);
    return {
      ...defaultConfig,
      id: businessId,
      name: `${businessId} Services`,
    };
  }

  return config;
}

/**
 * Get all available business configurations
 */
export function getAllBusinessConfigs(): BusinessConfig[] {
  return Object.values(businessConfigs);
}

/**
 * Check if a business ID exists
 */
export function isValidBusinessId(businessId: string): boolean {
  return businessId in businessConfigs;
}

/**
 * Get form prompts based on business type
 */
export function getBusinessPrompts(businessType: BusinessType) {
  const prompts = {
    automotive: {
      messagePlaceholder: "Describe your vehicle issue or service need (e.g., 'My 2019 Honda Civic makes a grinding noise when braking')",
      messageLabel: "What automotive service do you need?",
    },
    medspa: {
      messagePlaceholder: "Tell us about your wellness goals or treatment interest (e.g., 'I'm interested in anti-aging treatments for my face')",
      messageLabel: "What treatment are you interested in?",
    },
    consulting: {
      messagePlaceholder: "Describe your business challenge or project (e.g., 'We need help improving our marketing strategy')",
      messageLabel: "What business challenge can we help with?",
    },
    general: {
      messagePlaceholder: "Tell us how we can help you...",
      messageLabel: "How can we help you?",
    },
  };

  return prompts[businessType] || prompts.general;
}