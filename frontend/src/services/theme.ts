import type { BusinessConfig, ThemeMode } from '../types';

/**
 * Apply theme to the document
 */
export function applyTheme(config: BusinessConfig) {
  const root = document.documentElement;
  
  // Apply custom primary color
  root.style.setProperty('--primary-50', lightenColor(config.primaryColor, 95));
  root.style.setProperty('--primary-500', config.primaryColor);
  root.style.setProperty('--primary-600', darkenColor(config.primaryColor, 10));
  root.style.setProperty('--primary-700', darkenColor(config.primaryColor, 20));

  // Handle dark/light mode
  const isDarkMode = shouldUseDarkMode(config.theme);
  
  if (isDarkMode) {
    document.documentElement.classList.add('dark');
  } else {
    document.documentElement.classList.remove('dark');
  }
}

/**
 * Determine if dark mode should be used
 */
function shouldUseDarkMode(themeMode: ThemeMode): boolean {
  switch (themeMode) {
    case 'dark':
      return true;
    case 'light':
      return false;
    case 'auto':
    default:
      return window.matchMedia('(prefers-color-scheme: dark)').matches;
  }
}

/**
 * Lighten a hex color by a percentage
 */
function lightenColor(hex: string, percent: number): string {
  const color = hexToRgb(hex);
  if (!color) return hex;

  const { r, g, b } = color;
  const amount = Math.round(255 * (percent / 100));
  
  return rgbToHex(
    Math.min(255, r + amount),
    Math.min(255, g + amount),
    Math.min(255, b + amount)
  );
}

/**
 * Darken a hex color by a percentage
 */
function darkenColor(hex: string, percent: number): string {
  const color = hexToRgb(hex);
  if (!color) return hex;

  const { r, g, b } = color;
  const amount = Math.round(255 * (percent / 100));
  
  return rgbToHex(
    Math.max(0, r - amount),
    Math.max(0, g - amount),
    Math.max(0, b - amount)
  );
}

/**
 * Convert hex color to RGB
 */
function hexToRgb(hex: string): { r: number; g: number; b: number } | null {
  const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
  return result
    ? {
        r: parseInt(result[1], 16),
        g: parseInt(result[2], 16),
        b: parseInt(result[3], 16),
      }
    : null;
}

/**
 * Convert RGB to hex color
 */
function rgbToHex(r: number, g: number, b: number): string {
  return `#${[r, g, b].map(x => x.toString(16).padStart(2, '0')).join('')}`;
}