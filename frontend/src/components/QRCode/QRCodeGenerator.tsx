import { useState } from 'react';
import { QRCodeSVG } from 'qrcode.react';
import { Button } from '../UI/Button';
import { Input } from '../UI/Input';
import type { BusinessConfig, QRCodeConfig } from '../../types';

interface QRCodeGeneratorProps {
  business: BusinessConfig;
  baseUrl?: string;
}

export function QRCodeGenerator({ 
  business, 
  baseUrl = window.location.origin 
}: QRCodeGeneratorProps) {
  const [config, setConfig] = useState<QRCodeConfig>({
    businessId: business.id,
    source: 'qr',
    size: 256,
    includeText: true,
  });

  const [customSource, setCustomSource] = useState('');

  const generateUrl = (sourceParam: string = config.source || 'qr') => {
    return `${baseUrl}/form/${config.businessId}?source=${sourceParam}`;
  };

  const handleSizeChange = (size: number) => {
    setConfig(prev => ({ ...prev, size }));
  };

  const handleSourceChange = (source: string) => {
    setConfig(prev => ({ ...prev, source }));
  };

  const handleDownload = () => {
    const svg = document.querySelector('.qr-code-svg');
    if (!svg) return;

    // Create canvas and convert SVG to PNG
    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const data = new XMLSerializer().serializeToString(svg);
    const svgBlob = new Blob([data], { type: 'image/svg+xml;charset=utf-8' });
    const url = URL.createObjectURL(svgBlob);

    const img = new Image();
    img.onload = () => {
      canvas.width = config.size || 256;
      canvas.height = config.size || 256;
      ctx.drawImage(img, 0, 0);
      
      canvas.toBlob((blob) => {
        if (blob) {
          const downloadUrl = URL.createObjectURL(blob);
          const a = document.createElement('a');
          a.href = downloadUrl;
          a.download = `${business.name.replace(/\s+/g, '_')}_QR_Code.png`;
          document.body.appendChild(a);
          a.click();
          document.body.removeChild(a);
          URL.revokeObjectURL(downloadUrl);
        }
      }, 'image/png');
      
      URL.revokeObjectURL(url);
    };
    img.src = url;
  };

  const qrUrl = generateUrl();

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6">
      <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
        QR Code Generator - {business.name}
      </h3>

      {/* QR Code Display */}
      <div className="flex flex-col items-center mb-6">
        <div className="bg-white p-4 rounded-lg shadow-sm">
          <QRCodeSVG
            value={qrUrl}
            size={config.size}
            level="M"
            includeMargin={true}
            className="qr-code-svg"
          />
        </div>
        
        {config.includeText && (
          <div className="mt-4 text-center">
            <p className="text-sm font-medium text-gray-900 dark:text-white">
              {business.name}
            </p>
            <p className="text-xs text-gray-500 dark:text-gray-400">
              Scan to submit a lead
            </p>
          </div>
        )}
      </div>

      {/* Configuration Options */}
      <div className="space-y-4 mb-6">
        {/* Size Selection */}
        <div>
          <label className="form-label">QR Code Size</label>
          <div className="flex space-x-2">
            {[128, 192, 256, 320].map((size) => (
              <button
                key={size}
                onClick={() => handleSizeChange(size)}
                className={`px-3 py-1 text-sm rounded-md border ${
                  config.size === size
                    ? 'bg-primary-600 text-white border-primary-600'
                    : 'bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-300 border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-600'
                }`}
              >
                {size}px
              </button>
            ))}
          </div>
        </div>

        {/* Source Tracking */}
        <div>
          <label className="form-label">Source Parameter</label>
          <div className="space-y-2">
            {/* Preset sources */}
            <div className="flex flex-wrap gap-2">
              {['qr', 'print', 'flyer', 'business_card', 'poster'].map((source) => (
                <button
                  key={source}
                  onClick={() => handleSourceChange(source)}
                  className={`px-3 py-1 text-sm rounded-md border ${
                    config.source === source
                      ? 'bg-primary-600 text-white border-primary-600'
                      : 'bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-300 border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-600'
                  }`}
                >
                  {source.replace('_', ' ')}
                </button>
              ))}
            </div>
            
            {/* Custom source */}
            <div className="flex space-x-2">
              <Input
                placeholder="Custom source (e.g., magazine_ad)"
                value={customSource}
                onChange={(e) => setCustomSource(e.target.value)}
                className="text-sm"
              />
              <Button
                variant="secondary"
                size="sm"
                onClick={() => {
                  if (customSource.trim()) {
                    handleSourceChange(customSource.trim());
                    setCustomSource('');
                  }
                }}
                disabled={!customSource.trim()}
              >
                Add
              </Button>
            </div>
          </div>
        </div>

        {/* Include text toggle */}
        <div className="flex items-center">
          <input
            type="checkbox"
            id="includeText"
            checked={config.includeText}
            onChange={(e) => setConfig(prev => ({ ...prev, includeText: e.target.checked }))}
            className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
          />
          <label htmlFor="includeText" className="ml-2 text-sm text-gray-700 dark:text-gray-300">
            Include business name and instructions
          </label>
        </div>
      </div>

      {/* URL Preview */}
      <div className="mb-6">
        <label className="form-label">Generated URL</label>
        <div className="p-3 bg-gray-50 dark:bg-gray-700 rounded-md">
          <code className="text-xs text-gray-600 dark:text-gray-400 break-all">
            {qrUrl}
          </code>
        </div>
      </div>

      {/* Actions */}
      <div className="flex space-x-3">
        <Button
          onClick={handleDownload}
          className="flex-1"
        >
          Download PNG
        </Button>
        
        <Button
          variant="secondary"
          onClick={() => {
            navigator.clipboard.writeText(qrUrl);
            // Could add toast notification here
          }}
          className="flex-1"
        >
          Copy URL
        </Button>
      </div>

      {/* Usage Instructions */}
      <div className="mt-6 p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
        <h4 className="text-sm font-medium text-blue-900 dark:text-blue-300 mb-2">
          Usage Tips
        </h4>
        <ul className="text-xs text-blue-800 dark:text-blue-400 space-y-1">
          <li>• Use different source parameters to track where leads come from</li>
          <li>• Larger sizes (256px+) work better for print materials</li>
          <li>• Test the QR code with different phone cameras before printing</li>
          <li>• Include clear instructions near the QR code</li>
        </ul>
      </div>
    </div>
  );
}