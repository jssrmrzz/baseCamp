import { useEffect, useState } from 'react';
import { useParams, useSearchParams } from 'react-router-dom';
import { Layout } from '../components/UI/Layout';
import { Button } from '../components/UI/Button';
import { useBusinessStore } from '../hooks/useBusinessStore';

export function SuccessPage() {
  const { businessId } = useParams<{ businessId: string }>();
  const [searchParams] = useSearchParams();
  
  const { currentBusiness, setBusinessId } = useBusinessStore();
  const [isInitialized, setIsInitialized] = useState(false);

  const leadId = searchParams.get('leadId');
  const source = searchParams.get('source') || 'hosted_form';

  useEffect(() => {
    if (businessId && !isInitialized) {
      setBusinessId(businessId);
      setIsInitialized(true);
    }
  }, [businessId, setBusinessId, isInitialized]);

  const handleSubmitAnother = () => {
    const baseUrl = `/form/${businessId}`;
    const sourceParam = source !== 'hosted_form' ? `?source=${source}` : '';
    window.location.href = `${baseUrl}${sourceParam}`;
  };

  const getSuccessMessage = () => {
    if (!currentBusiness) return '';

    switch (currentBusiness.businessType) {
      case 'automotive':
        return "We'll review your vehicle concern and contact you soon to schedule service or provide guidance.";
      case 'medspa':
        return "We'll review your treatment inquiry and contact you to discuss options and schedule a consultation.";
      case 'consulting':
        return "We'll review your business needs and contact you to discuss how we can help achieve your goals.";
      default:
        return "We'll review your request and contact you soon to discuss next steps.";
    }
  };

  const getNextSteps = () => {
    if (!currentBusiness) return [];

    switch (currentBusiness.businessType) {
      case 'automotive':
        return [
          'Review your vehicle information and symptoms',
          'Check our service availability',
          'Contact you within 24 hours to schedule',
        ];
      case 'medspa':
        return [
          'Review your treatment interests and goals',
          'Check availability for consultations',
          'Contact you to schedule your appointment',
        ];
      case 'consulting':
        return [
          'Analyze your business challenges and needs',
          'Prepare preliminary recommendations',
          'Schedule a discovery call to discuss solutions',
        ];
      default:
        return [
          'Review your request details',
          'Prepare our response',
          'Contact you to discuss next steps',
        ];
    }
  };

  if (!isInitialized) {
    return (
      <Layout>
        <div className="p-6 text-center">
          <div className="animate-spin mx-auto h-8 w-8 border-4 border-primary-500 border-t-transparent rounded-full"></div>
        </div>
      </Layout>
    );
  }

  return (
    <Layout business={currentBusiness || undefined}>
      <div className="p-6 text-center">
        {/* Success Icon */}
        <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-green-100 dark:bg-green-900/20">
          <svg
            className="h-8 w-8 text-green-600 dark:text-green-400"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M5 13l4 4L19 7"
            />
          </svg>
        </div>

        {/* Success Message */}
        <h2 className="mt-6 text-2xl font-bold text-gray-900 dark:text-white">
          Thank You!
        </h2>
        
        <p className="mt-2 text-lg text-gray-600 dark:text-gray-400">
          Your request has been submitted successfully.
        </p>

        {leadId && (
          <p className="mt-2 text-sm text-gray-500 dark:text-gray-500">
            Reference ID: <span className="font-mono">{leadId}</span>
          </p>
        )}

        {/* What Happens Next */}
        <div className="mt-8 text-left">
          <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
            What happens next?
          </h3>
          
          <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
            {getSuccessMessage()}
          </p>

          <div className="space-y-3">
            {getNextSteps().map((step, index) => (
              <div key={index} className="flex items-start">
                <div className="flex-shrink-0 h-6 w-6 rounded-full bg-primary-100 dark:bg-primary-900/20 flex items-center justify-center mr-3">
                  <span className="text-xs font-medium text-primary-600 dark:text-primary-400">
                    {index + 1}
                  </span>
                </div>
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  {step}
                </p>
              </div>
            ))}
          </div>
        </div>

        {/* Contact Info */}
        <div className="mt-8 p-4 bg-gray-50 dark:bg-gray-800/50 rounded-lg">
          <h4 className="font-medium text-gray-900 dark:text-white mb-2">
            Need immediate assistance?
          </h4>
          <p className="text-sm text-gray-600 dark:text-gray-400">
            If you have an urgent request, please call us directly or email us at{' '}
            <a href="mailto:info@example.com" className="text-primary-600 dark:text-primary-400 hover:underline">
              info@example.com
            </a>
          </p>
        </div>

        {/* Actions */}
        <div className="mt-8 space-y-3">
          <Button
            variant="secondary"
            onClick={handleSubmitAnother}
            className="w-full"
          >
            Submit Another Request
          </Button>
          
          {currentBusiness?.logoUrl && (
            <p className="text-xs text-gray-500 dark:text-gray-400">
              Visit our website for more information
            </p>
          )}
        </div>

        {/* Source tracking (hidden) */}
        {source !== 'hosted_form' && (
          <div className="hidden">
            Source: {source}
          </div>
        )}
      </div>
    </Layout>
  );
}