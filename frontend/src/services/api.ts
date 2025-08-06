import type { LeadFormData, LeadSubmissionResponse } from '../types';

class BaseCampAPI {
  private baseUrl: string;

  constructor() {
    // In development, use localhost:8000; in production, use environment variable or same origin
    this.baseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
  }

  /**
   * Submit a lead to the baseCamp intake API
   */
  async submitLead(data: LeadFormData): Promise<LeadSubmissionResponse> {
    try {
      const response = await fetch(`${this.baseUrl}/api/v1/intake`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: data.message,
          contact: {
            first_name: data.contact.name,
            email: data.contact.email || null,
            phone: data.contact.phone || null,
          },
          source: data.source === 'hosted_form' ? 'web_form' : data.source,
        }),
      });

      const result = await response.json();

      if (!response.ok) {
        throw new ApiError(
          result.detail || 'Submission failed',
          response.status
        );
      }

      return {
        success: true,
        id: result.lead_id,
        message: result.message || 'Lead submitted successfully',
      };
    } catch (error) {
      console.error('API Error:', error);
      
      if (error instanceof ApiError) {
        return {
          success: false,
          error: error.message,
        };
      }

      // Network or other errors
      return {
        success: false,
        error: 'Unable to submit lead. Please check your connection and try again.',
      };
    }
  }

  /**
   * Check if the API is healthy
   */
  async healthCheck(): Promise<boolean> {
    try {
      const response = await fetch(`${this.baseUrl}/api/v1/health`);
      return response.ok;
    } catch {
      return false;
    }
  }
}

// Custom API Error class
class ApiError extends Error {
  status?: number;

  constructor(message: string, status?: number) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

// Export singleton instance
export const baseCampAPI = new BaseCampAPI();
export { ApiError };