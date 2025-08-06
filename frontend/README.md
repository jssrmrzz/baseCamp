# baseCamp Frontend - Lead Capture Forms

A React TypeScript frontend for baseCamp's hosted lead capture forms with QR code integration.

## 🚀 Features

### Hosted Lead Capture Forms
- **Dynamic Business Configuration**: Form customization based on business type
- **Mobile-First Design**: Responsive forms optimized for all devices
- **Smart Validation**: Client-side validation with Zod schema
- **Error Handling**: Comprehensive error states and user feedback
- **Success Flow**: Confirmation pages with business-specific messaging

### QR Code Integration
- **Dynamic QR Generation**: Create QR codes linking to forms
- **Source Tracking**: Track lead sources (QR, print, digital)
- **Customizable**: Multiple sizes and source parameters
- **Download Support**: Export QR codes as PNG files

### Business Types Supported
- **Automotive**: Vehicle service and repair forms
- **MedSpa**: Beauty and wellness treatment inquiries  
- **Consulting**: Business service consultations
- **General**: Flexible forms for any business type

## 🛠 Tech Stack

- **React 18** with TypeScript
- **Vite** for build tooling and development
- **Tailwind CSS** for styling and responsive design
- **React Router** for client-side routing
- **React Hook Form** with Zod validation
- **Zustand** for state management
- **QR Code Generation** with `qrcode.react`

## 🚀 Getting Started

### Prerequisites
- Node.js 18+ with npm
- baseCamp API server running on localhost:8000

### Installation

1. Install dependencies:
   ```bash
   npm install
   ```

2. Create environment configuration:
   ```bash
   cp .env.example .env
   ```

3. Update `.env` with your configuration:
   ```env
   VITE_API_BASE_URL=http://localhost:8000
   VITE_NODE_ENV=development
   ```

### Development

Start the development server:
```bash
npm run dev
```

The application will be available at `http://localhost:5173`

### Building for Production

Build the project:
```bash
npm run build
```

Preview the production build:
```bash
npm run preview
```

## 📱 URL Patterns

### Hosted Forms
- **Main Form**: `/form/:businessId`
- **Success Page**: `/form/:businessId/success`
- **With Source Tracking**: `/form/:businessId?source=qr`

### Demo Business IDs
- `demo-auto` - Automotive service business
- `demo-medspa` - Medical spa and wellness
- `demo-consulting` - Business consulting services
- `demo-general` - General service business

### Example URLs
```
http://localhost:5173/form/demo-auto
http://localhost:5173/form/demo-medspa?source=qr
http://localhost:5173/form/demo-consulting?source=business_card
```

## 🎨 Customization

### Business Configuration

Edit `src/services/businessConfig.ts` to add new businesses:

```typescript
const businessConfigs = {
  'your-business-id': {
    id: 'your-business-id',
    name: 'Your Business Name',
    businessType: 'automotive', // or 'medspa', 'consulting', 'general'
    theme: 'light', // or 'dark', 'auto'
    primaryColor: '#dc2626', // Brand color
    description: 'Your business description',
  },
};
```

## 🔧 API Integration

The frontend connects to the baseCamp API at `/api/v1/intake`:

```typescript
// Form submission payload
{
  message: string,
  contact: {
    name: string,
    email?: string,
    phone?: string,
  },
  business_id: string,
  source: string,
  timestamp: string,
}
```

## 🚀 Deployment

### Vercel (Recommended)
1. Connect GitHub repository
2. Set environment variables in Vercel dashboard
3. Deploy automatically on push to main

### Build Commands
```bash
npm run dev          # Start development server
npm run build        # Build for production  
npm run preview      # Preview production build
```

## 🚧 Current Known Issues

### CORS Preflight Request Blocking (Critical)
**Status**: Backend issue preventing form submissions

**Symptoms:**
- Forms validate and load correctly
- All UI components work properly
- Form submission fails with CORS error
- Browser console shows: `blocked by CORS policy`

**Root Cause**: 
SlowAPI rate limiter in backend interfering with CORS preflight OPTIONS requests.

**Workaround for Development:**
1. All frontend features work except final submission
2. Form validation can be tested completely
3. QR code generation works fully
4. UI/UX testing is unaffected

**Resolution Status**: 
Backend CORS configuration needs debugging. Frontend is 100% complete and ready.

## 🔧 Troubleshooting

### Frontend Won't Start
```bash
# Clear cache and reinstall
rm -rf node_modules package-lock.json
npm install
npm run dev
```

### Build Errors
```bash
# Check TypeScript compilation
npm run build
# Address any TypeScript issues shown
```

### API Connection Issues
1. Verify backend is running on `http://localhost:8000`
2. Check backend health: `http://localhost:8000/api/v1/health`
3. Confirm CORS origins include `http://localhost:5173`
4. Check browser Network tab for specific error details

### Form Validation Testing
Even with CORS issues, you can test:
- Form field validation
- Client-side error messages  
- Business configuration loading
- QR code generation and download
- Responsive design across devices
- Success page navigation (via direct URL)

## 📊 Current Status

**Frontend Completion**: ✅ 100% - Production ready
**Backend Integration**: 🚧 Blocked on CORS resolution
**Recommended Testing**: Focus on UI/UX and form validation while CORS is resolved
