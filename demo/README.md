# baseCamp Demo Instances

This directory contains tools and configurations for setting up demonstration instances of baseCamp for different business types.

## 🎯 Purpose

Demo instances allow you to:
- Show prospects how baseCamp works in their industry
- Test the system with realistic scenarios  
- Demonstrate AI analysis capabilities
- Showcase CRM integration
- Provide hands-on experience before purchase

## 🏗️ Quick Setup

### Interactive Setup (Recommended)
```bash
python demo/demo-setup.py --interactive
```

### Specific Business Type
```bash
python demo/demo-setup.py --business-type automotive --demo-domain demo-auto.example.com
```

### All Business Types
```bash
python demo/demo-setup.py --all-business-types
```

## 📋 Business Types Available

### 🔧 Automotive
- **Focus**: Car repair and maintenance
- **Sample Scenarios**: Emergency brake repairs, oil changes, diagnostics
- **Key Features**: Vehicle identification, urgency detection, service classification

### 💄 Medical Spa (MedSpa)
- **Focus**: Beauty and wellness treatments
- **Sample Scenarios**: Botox consultations, laser treatments, wedding packages
- **Key Features**: Treatment categorization, consultation scheduling, package inquiries

### 💼 Business Consulting
- **Focus**: Strategic consulting services
- **Sample Scenarios**: Digital transformation, startup strategy, process optimization
- **Key Features**: Project scoping, budget detection, expertise matching

### 🏢 General Business
- **Focus**: Multi-purpose business template
- **Sample Scenarios**: Service inquiries, support requests, general questions
- **Key Features**: Flexible intent classification, customizable categories

## 🛠️ Demo Setup Process

### 1. Generate Demo Files
The setup script creates:
- `{business_type}_scenarios.json` - Sample customer scenarios
- `{business_type}_demo_guide.md` - Demo script and documentation
- `{business_type}_airtable_config.json` - CRM table configuration
- `load-sample-data.py` - Script to populate demo data

### 2. Deploy Demo Instance
```bash
# Provision demo client
scripts/provision-client.sh demo-{business-type} \
  --domain demo-{business-type}.example.com \
  --business-type {business-type}
```

### 3. Configure Airtable
1. Create new Airtable base
2. Use the generated `airtable_config.json` for table structure
3. Update demo client's `.env.production` with Airtable credentials

### 4. Load Sample Data
```bash
demo/load-sample-data.py \
  --demo-url https://demo-{business-type}.example.com \
  --scenarios demo/{business_type}_scenarios.json
```

## 📖 Demo Scripts

Each demo guide includes:
- **Overview**: Business-specific value proposition
- **Sample Scenarios**: Realistic customer inquiries with expected AI analysis
- **Demo Script**: Step-by-step presentation guide
- **Key Features**: Technical highlights and business benefits
- **Setup Instructions**: Deployment and configuration steps

## 🎪 Running a Demo

### Preparation (5 minutes)
1. Review the demo guide for your business type
2. Ensure demo instance is healthy: `scripts/health-check.sh --client demo-{business-type}`
3. Pre-load sample scenarios or prepare to submit live
4. Have Airtable base open to show real-time integration

### Demo Flow (20 minutes)
1. **Introduction** (3 min): System overview and value proposition
2. **Form Submission** (5 min): Show customer experience
3. **AI Analysis** (5 min): Highlight intelligent processing
4. **CRM Integration** (4 min): Demonstrate data flow
5. **Q&A and Next Steps** (3 min): Address questions and discuss implementation

### Technical Deep-Dive (Optional 10 minutes)
- Architecture overview
- Security and privacy features  
- Scalability and performance
- Integration capabilities
- Deployment options

## 🔍 Sample Scenarios

### Automotive Example
**Customer Message:**
> "My 2019 Honda Civic makes a grinding noise when I brake. It started this morning and I'm worried it's not safe to drive. Can someone look at it today?"

**AI Analysis:**
- **Intent**: `appointment_request` (90% confidence)
- **Urgency**: `0.9` (High - safety concern, same-day request)
- **Entities**: 2019 Honda Civic, brake issue, grinding noise
- **Service Type**: Emergency brake repair
- **Lead Quality**: `85` (Complete info, clear need, contactable)

### MedSpa Example
**Customer Message:**
> "Getting married in 3 months and want to look my best! Interested in a facial package, maybe some laser treatments. What packages do you offer?"

**AI Analysis:**
- **Intent**: `package_inquiry` (85% confidence)  
- **Urgency**: `0.7` (High - wedding timeline)
- **Entities**: Wedding, 3 months, facial, laser treatments
- **Treatments**: Multiple service interest
- **Lead Quality**: `78` (Motivated buyer, specific timeline)

## 📊 Demo Metrics to Highlight

### Time Savings
- Manual lead processing: 5-10 minutes per lead
- Automated processing: 10-15 seconds per lead  
- **Savings**: 95%+ time reduction

### Lead Quality Improvement
- Better categorization and prioritization
- Reduced missed opportunities  
- Faster response times
- **Result**: 30%+ increase in conversion rates

### CRM Integration Benefits
- Automatic data entry eliminates errors
- Consistent formatting and categorization
- Real-time availability for sales team
- **Result**: 100% lead capture rate

## 🛠️ Customization

### Adding Custom Scenarios
Edit the scenarios JSON file to add business-specific examples:
```json
{
  "name": "Custom Scenario Name",
  "message": "Customer inquiry text...",
  "contact": {
    "first_name": "John",
    "last_name": "Doe", 
    "email": "john@example.com",
    "phone": "555-0123"
  },
  "expected_intent": "service_request",
  "expected_urgency": 0.7
}
```

### Branding Customization
Update client environment variables:
- Company name and logo
- Color scheme and styling  
- Custom form fields
- Business-specific terminology

### Integration Customization
- Connect to client's actual Airtable
- Configure field mappings
- Set up webhook notifications
- Add custom business rules

## 🔧 Maintenance

### Health Monitoring
```bash
# Check all demo instances
scripts/health-check.sh --all

# Check specific demo
scripts/health-check.sh --client demo-automotive
```

### Updates
```bash
# Update demo configurations
python demo/demo-setup.py --business-type automotive --demo-domain demo-auto.example.com

# Redeploy demo instance  
clients/demo-automotive/deploy.sh
```

### Cleanup
```bash
# Remove demo instance
docker-compose -f docker-compose.prod.yml -f clients/demo-automotive/docker-compose.override.yml down
rm -rf clients/demo-automotive
```

## 📞 Support

For demo setup assistance:
1. Check the business-specific demo guide  
2. Review health check outputs
3. Validate configuration with `scripts/validate-production.py`
4. Check container logs for detailed error information

---

*Generated by baseCamp Demo System*