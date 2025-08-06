import { useEffect, useState } from 'react';
import { useParams, useSearchParams, useNavigate } from 'react-router-dom';
import { Layout } from '../components/UI/Layout';
import { LeadForm } from '../components/LeadForm/LeadForm';
import { useBusinessStore } from '../hooks/useBusinessStore';

export function FormPage() {
  const { businessId } = useParams<{ businessId: string }>();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  
  const { currentBusiness, isBusinessLoading, setBusinessId } = useBusinessStore();
  const [isInitialized, setIsInitialized] = useState(false);

  // Get source from URL parameters (e.g., ?source=qr)
  const source = searchParams.get('source') || 'hosted_form';

  useEffect(() => {
    if (businessId && !isInitialized) {
      setBusinessId(businessId);
      setIsInitialized(true);
    }
  }, [businessId, setBusinessId, isInitialized]);

  const handleFormSuccess = (leadId: string) => {
    // Navigate to success page with lead ID
    navigate(`/form/${businessId}/success?leadId=${leadId}&source=${source}`);
  };

  const handleFormError = (error: string) => {
    console.error('Form submission error:', error);
    // Error is already shown in the form component
  };

  // Loading state
  if (!businessId) {
    return (
      <Layout>
        <div className="p-6 text-center">
          <h2 className="text-lg font-medium text-gray-900 dark:text-white">
            Invalid URL
          </h2>
          <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
            Please check the URL and try again.
          </p>
        </div>
      </Layout>
    );
  }

  if (isBusinessLoading || !isInitialized) {
    return (
      <Layout>
        <div className="p-6 text-center">
          <div className="animate-spin mx-auto h-8 w-8 border-4 border-primary-500 border-t-transparent rounded-full"></div>
          <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
            Loading...
          </p>
        </div>
      </Layout>
    );
  }

  if (!currentBusiness) {
    return (
      <Layout>
        <div className="p-6 text-center">
          <h2 className="text-lg font-medium text-gray-900 dark:text-white">
            Business Not Found
          </h2>
          <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
            The business you're looking for could not be found.
          </p>
        </div>
      </Layout>
    );
  }

  return (
    <Layout business={currentBusiness}>
      <LeadForm
        business={currentBusiness}
        source={source}
        onSuccess={handleFormSuccess}
        onError={handleFormError}
      />
    </Layout>
  );
}