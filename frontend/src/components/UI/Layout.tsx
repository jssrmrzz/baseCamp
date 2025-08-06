import type { BusinessConfig } from '../../types';

interface LayoutProps {
  children: React.ReactNode;
  business?: BusinessConfig;
}

export function Layout({ children, business }: LayoutProps) {
  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <div className="mx-auto max-w-md px-4 py-8 sm:max-w-lg sm:px-6">
        {business && (
          <div className="mb-8 text-center">
            {business.logoUrl && (
              <img
                src={business.logoUrl}
                alt={`${business.name} logo`}
                className="mx-auto mb-4 h-16 w-auto"
              />
            )}
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
              {business.name}
            </h1>
            {business.description && (
              <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
                {business.description}
              </p>
            )}
          </div>
        )}
        
        <main className="bg-white dark:bg-gray-800 shadow-sm rounded-lg">
          {children}
        </main>
        
        <footer className="mt-8 text-center">
          <p className="text-xs text-gray-500 dark:text-gray-400">
            Powered by baseCamp
          </p>
        </footer>
      </div>
    </div>
  );
}