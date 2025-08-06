import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import type { BusinessConfig, LeadFormData } from '../../types';
import { leadFormSchema, type LeadFormInput, validateContactInfo } from '../../utils/validation';
import { getBusinessPrompts } from '../../services/businessConfig';
import { Button } from '../UI/Button';
import { Input, Textarea } from '../UI/Input';
import { baseCampAPI } from '../../services/api';

interface LeadFormProps {
  business: BusinessConfig;
  source?: string;
  onSuccess?: (leadId: string) => void;
  onError?: (error: string) => void;
}

export function LeadForm({ 
  business, 
  source = 'hosted_form', 
  onSuccess, 
  onError 
}: LeadFormProps) {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  
  const prompts = getBusinessPrompts(business.businessType);

  const {
    register,
    handleSubmit,
    formState: { errors },
    setError,
    clearErrors,
  } = useForm<LeadFormInput>({
    resolver: zodResolver(leadFormSchema),
    defaultValues: {
      businessId: business.id,
      source,
      contact: {
        name: '',
        email: '',
        phone: '',
      },
      message: '',
    },
  });

  // const watchedContact = watch('contact');

  const onSubmit = async (data: LeadFormInput) => {
    setIsSubmitting(true);
    setSubmitError(null);
    clearErrors();

    // Validate that at least one contact method is provided
    const contactError = validateContactInfo(data.contact);
    if (contactError) {
      setError('contact', { message: contactError });
      setIsSubmitting(false);
      return;
    }

    try {
      const leadData: LeadFormData = {
        ...data,
        contact: {
          name: data.contact.name,
          email: data.contact.email || undefined,
          phone: data.contact.phone || undefined,
        },
      };

      const result = await baseCampAPI.submitLead(leadData);

      if (result.success && result.id) {
        onSuccess?.(result.id);
      } else {
        const errorMessage = result.error || 'Submission failed';
        setSubmitError(errorMessage);
        onError?.(errorMessage);
      }
    } catch (error) {
      const errorMessage = 'Unable to submit your request. Please try again.';
      setSubmitError(errorMessage);
      onError?.(errorMessage);
      console.error('Form submission error:', error);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="p-6">
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
        {/* Message field */}
        <div>
          <Textarea
            label={prompts.messageLabel}
            placeholder={prompts.messagePlaceholder}
            rows={4}
            error={errors.message?.message}
            {...register('message')}
          />
        </div>

        {/* Contact Information */}
        <div className="space-y-4">
          <h3 className="text-lg font-medium text-gray-900 dark:text-white">
            Contact Information
          </h3>
          
          <Input
            label="Your Name *"
            type="text"
            placeholder="Enter your full name"
            error={errors.contact?.name?.message}
            {...register('contact.name')}
          />

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <Input
              label="Email Address"
              type="email"
              placeholder="your@email.com"
              error={errors.contact?.email?.message}
              {...register('contact.email')}
            />

            <Input
              label="Phone Number"
              type="tel"
              placeholder="(555) 123-4567"
              error={errors.contact?.phone?.message}
              {...register('contact.phone')}
            />
          </div>

          {errors.contact?.message && (
            <p className="text-sm text-red-600 dark:text-red-400">
              {errors.contact.message}
            </p>
          )}

          <p className="text-xs text-gray-500 dark:text-gray-400">
            * Required field. Please provide either an email or phone number so we can contact you.
          </p>
        </div>

        {/* Submit button */}
        <div className="pt-4">
          {submitError && (
            <div className="mb-4 rounded-md bg-red-50 dark:bg-red-900/20 p-4">
              <p className="text-sm text-red-600 dark:text-red-400">
                {submitError}
              </p>
            </div>
          )}

          <Button
            type="submit"
            size="lg"
            isLoading={isSubmitting}
            disabled={isSubmitting}
            className="w-full"
          >
            {isSubmitting ? 'Submitting...' : 'Submit Request'}
          </Button>
        </div>
      </form>

      {/* Trust indicators */}
      <div className="mt-6 border-t border-gray-200 dark:border-gray-700 pt-4">
        <p className="text-xs text-center text-gray-500 dark:text-gray-400">
          🔒 Your information is secure and will only be used to contact you about your request
        </p>
      </div>
    </div>
  );
}