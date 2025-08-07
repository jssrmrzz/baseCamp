# baseCamp Demo: Automotive Repair Shop

## Overview
This demo showcases baseCamp's AI-powered lead intake and enrichment system specifically configured for Car repair and maintenance services.

## Demo URL
🌐 **Demo Instance**: https://DomShop

## Business Type Configuration
- **Industry**: Automotive Repair Shop  
- **AI Optimization**: Specialized prompts for automotive industry
- **Lead Processing**: Industry-specific intent classification and entity extraction

## Sample Scenarios

### What to Demo

### 1. Brake Repair Emergency

**Sample Message:**
```
My 2019 Honda Civic makes a grinding noise when I brake. It started this morning and I'm worried it's not safe to drive. Can someone look at it today?
```

**Contact Info:**
- Name: Sarah Johnson
- Email: sarah.j@email.com
- Phone: 555-0123

**Expected AI Analysis:**
- Intent: `appointment_request`
- Urgency Score: `0.9`

**Demo Points:**
- Show how AI correctly identifies the intent
- Highlight industry-specific entity extraction
- Demonstrate urgency scoring based on keywords

### 2. Regular Oil Change

**Sample Message:**
```
Hi, I need to schedule an oil change for my 2020 Toyota Camry. I'm flexible on timing, just sometime next week would be great.
```

**Contact Info:**
- Name: Mike Chen
- Email: mike.chen@email.com
- Phone: 555-0456

**Expected AI Analysis:**
- Intent: `service_request`
- Urgency Score: `0.3`

**Demo Points:**
- Show how AI correctly identifies the intent
- Highlight industry-specific entity extraction
- Demonstrate urgency scoring based on keywords

### 3. Check Engine Light

**Sample Message:**
```
Check engine light came on in my 2018 Ford F-150. Truck seems to run fine but want to get it diagnosed. What would this cost?
```

**Contact Info:**
- Name: David Rodriguez
- Email: d.rodriguez@email.com
- Phone: 555-0789

**Expected AI Analysis:**
- Intent: `quote_request`
- Urgency Score: `0.6`

**Demo Points:**
- Show how AI correctly identifies the intent
- Highlight industry-specific entity extraction
- Demonstrate urgency scoring based on keywords


## Demo Script

### 1. Introduction (2 minutes)
"This is baseCamp, an AI-powered lead intake system designed specifically for Car repair and maintenance services. It automatically processes customer inquiries, analyzes intent and urgency, and integrates directly with your CRM."

### 2. Form Submission Demo (5 minutes)
- Use one of the high-urgency scenarios (like "Brake Repair Emergency")
- Show the form submission process
- Highlight the clean, professional interface

### 3. AI Analysis Showcase (5 minutes)
- Show the processing pipeline in real-time
- Demonstrate the AI's analysis results
- Explain industry-specific optimization
- Show the structured output with confidence scores

### 4. CRM Integration (3 minutes)
- Show the lead appearing in Airtable immediately
- Demonstrate the field mapping and data enrichment
- Show how similar leads are detected and flagged

### 5. Business Value Discussion (5 minutes)
- Highlight time savings (manual processing vs automated)
- Show lead qualification improvements
- Discuss ROI and efficiency gains

## Key Features to Highlight

### 🤖 AI-Powered Analysis
- Industry-specific prompt engineering
- Intent classification with 90%+ accuracy
- Automatic urgency scoring
- Entity extraction (vehicles, services, dates, etc.)

### 🎯 Smart Lead Processing
- Duplicate detection prevents lead loss
- Quality scoring helps prioritize follow-up
- Background processing for fast response times

### 🔗 Seamless CRM Integration
- Real-time Airtable synchronization
- Configurable field mapping
- Bi-directional sync capabilities

### 📊 Business Intelligence
- Lead source tracking
- Intent distribution analysis
- Response time monitoring
- Quality metrics and trends

## Technical Details for Technical Prospects

### Architecture
- Container-based deployment (Docker)
- Microservices architecture
- Local LLM processing (Ollama + Mistral)
- Vector similarity search (ChromaDB)
- Production-ready infrastructure

### Security & Privacy
- Container isolation per client
- Local data processing (no external AI calls)
- SSL/TLS encryption
- API rate limiting and validation

### Scalability
- Horizontal scaling support
- Resource-based container limits
- Background job processing
- Caching layer for performance

## Setup Instructions

### Prerequisites
- Domain configured: `DomShop`
- Airtable base created with demo scenarios
- SSL certificates installed

### Quick Start
```bash
# Create demo client
./scripts/provision-client.sh demo-automotive --domain DomShop --business-type automotive

# Load sample scenarios (optional)
python demo/load-sample-data.py --client demo-automotive --scenarios demo/automotive_scenarios.json
```

### Customization
- Update business name and branding in environment variables
- Customize form fields and styling
- Add business-specific scenarios
- Configure Airtable integration

## Troubleshooting

### Common Issues
1. **SSL Certificate Issues**: Ensure DNS points to server before SSL setup
2. **Airtable Connection**: Verify API key and base ID in configuration
3. **Container Issues**: Check Docker logs for specific service errors

### Health Checks
```bash
# Check all services
./scripts/health-check.sh --client demo-automotive

# Validate configuration
python scripts/validate-production.py --client demo-automotive
```

## Next Steps for Prospects

### Trial Setup
1. Configure their domain and SSL
2. Connect their Airtable account
3. Customize forms with their branding
4. Import their existing lead data

### Production Deployment
1. VPS provisioning and setup
2. Custom domain configuration
3. Business-specific prompt tuning
4. Team training and onboarding

---

*Generated by baseCamp Demo Setup*
*Business Type: automotive*
*Demo Domain: DomShop*
*Created: $(date)*
