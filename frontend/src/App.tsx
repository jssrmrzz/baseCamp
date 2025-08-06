import { useState } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { FormPage } from './pages/FormPage';
import { SuccessPage } from './pages/SuccessPage';
import { QRCodeGenerator } from './components/QRCode/QRCodeGenerator';
import { getAllBusinessConfigs } from './services/businessConfig';
import './App.css';

function App() {
  return (
    <Router>
      <div className="App">
        <Routes>
          {/* Form routes */}
          <Route path="/form/:businessId" element={<FormPage />} />
          <Route path="/form/:businessId/success" element={<SuccessPage />} />
          
          {/* Demo/development routes */}
          <Route path="/" element={<DemoPage />} />
          
          {/* Catch all - redirect to demo */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </div>
    </Router>
  );
}

// Demo page for development and testing
function DemoPage() {
  const businesses = getAllBusinessConfigs();
  const [selectedBusinessForQR, setSelectedBusinessForQR] = useState<string | null>(null);

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 py-12">
      <div className="mx-auto max-w-4xl px-4">
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold text-gray-900 dark:text-white">
            baseCamp Lead Capture
          </h1>
          <p className="mt-4 text-lg text-gray-600 dark:text-gray-400">
            Hosted forms for small business lead capture
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          {businesses.map((business) => (
            <div
              key={business.id}
              className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6"
            >
              <div className="flex items-center mb-4">
                <div 
                  className="w-4 h-4 rounded-full mr-3"
                  style={{ backgroundColor: business.primaryColor }}
                />
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                  {business.name}
                </h3>
              </div>
              
              <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
                {business.description}
              </p>
              
              <div className="text-xs text-gray-500 dark:text-gray-500 mb-4">
                Business Type: {business.businessType}
              </div>

              <div className="space-y-3">
                <a
                  href={`/form/${business.id}`}
                  className="block w-full text-center px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
                >
                  View Form
                </a>
                
                <a
                  href={`/form/${business.id}?source=qr`}
                  className="block w-full text-center px-4 py-2 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 rounded-md hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
                >
                  View Form (QR Source)
                </a>
              </div>
            </div>
          ))}
        </div>

        <div className="mt-12">
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-4 text-center">
            QR Code Integration
          </h2>
          <p className="text-gray-600 dark:text-gray-400 mb-6 text-center">
            Generate QR codes that link directly to your hosted forms
          </p>
          
          {!selectedBusinessForQR ? (
            <div className="text-center">
              <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
                Select a business to generate QR codes:
              </p>
              <div className="flex flex-wrap justify-center gap-2">
                {businesses.map((business) => (
                  <button
                    key={business.id}
                    onClick={() => setSelectedBusinessForQR(business.id)}
                    className="px-4 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700 transition-colors"
                  >
                    {business.name}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div>
              <div className="mb-4 text-center">
                <button
                  onClick={() => setSelectedBusinessForQR(null)}
                  className="text-sm text-primary-600 dark:text-primary-400 hover:underline"
                >
                  ← Back to business selection
                </button>
              </div>
              <QRCodeGenerator 
                business={businesses.find(b => b.id === selectedBusinessForQR)!}
              />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default App;
