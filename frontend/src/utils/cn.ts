import { type ClassValue, clsx } from 'clsx';

/**
 * Utility function to conditionally join classNames
 * Uses clsx for className concatenation
 */
export function cn(...inputs: ClassValue[]) {
  return clsx(inputs);
}