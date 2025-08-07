#!/usr/bin/env python3
"""
baseCamp Demo Instance Setup

Creates demo instances for different business types with sample data
and realistic scenarios to show prospects.

Usage:
    python demo/demo-setup.py --business-type automotive --demo-domain demo-auto.basecamp.example.com
    python demo/demo-setup.py --all-business-types
    python demo/demo-setup.py --interactive
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional
import subprocess
import shutil


class DemoSetup:
    """Sets up baseCamp demo instances."""
    
    BUSINESS_TYPES = {
        'automotive': {
            'display_name': 'Automotive Repair Shop',
            'description': 'Car repair and maintenance services',
            'sample_scenarios': [
                {
                    'name': 'Brake Repair Emergency',
                    'message': 'My 2019 Honda Civic makes a grinding noise when I brake. It started this morning and I\'m worried it\'s not safe to drive. Can someone look at it today?',
                    'contact': {'first_name': 'Sarah', 'last_name': 'Johnson', 'email': 'sarah.j@email.com', 'phone': '555-0123'},
                    'expected_intent': 'appointment_request',
                    'expected_urgency': 0.9
                },
                {
                    'name': 'Regular Oil Change',
                    'message': 'Hi, I need to schedule an oil change for my 2020 Toyota Camry. I\'m flexible on timing, just sometime next week would be great.',
                    'contact': {'first_name': 'Mike', 'last_name': 'Chen', 'email': 'mike.chen@email.com', 'phone': '555-0456'},
                    'expected_intent': 'service_request',
                    'expected_urgency': 0.3
                },
                {
                    'name': 'Check Engine Light',
                    'message': 'Check engine light came on in my 2018 Ford F-150. Truck seems to run fine but want to get it diagnosed. What would this cost?',
                    'contact': {'first_name': 'David', 'last_name': 'Rodriguez', 'email': 'd.rodriguez@email.com', 'phone': '555-0789'},
                    'expected_intent': 'quote_request',
                    'expected_urgency': 0.6
                }
            ]
        },
        'medspa': {
            'display_name': 'Medical Spa',
            'description': 'Beauty and wellness treatments',
            'sample_scenarios': [
                {
                    'name': 'Botox Consultation',
                    'message': 'I\'m interested in Botox for forehead lines. This would be my first time. Can I schedule a consultation to discuss options and pricing?',
                    'contact': {'first_name': 'Jennifer', 'last_name': 'Smith', 'email': 'jen.smith@email.com', 'phone': '555-1234'},
                    'expected_intent': 'consultation_request',
                    'expected_urgency': 0.5
                },
                {
                    'name': 'Wedding Preparation Package',
                    'message': 'Getting married in 3 months and want to look my best! Interested in a facial package, maybe some laser treatments. What packages do you offer?',
                    'contact': {'first_name': 'Amanda', 'last_name': 'Davis', 'email': 'amanda.davis@email.com', 'phone': '555-2468'},
                    'expected_intent': 'package_inquiry',
                    'expected_urgency': 0.7
                },
                {
                    'name': 'Laser Hair Removal Question',
                    'message': 'How many sessions would I need for laser hair removal on legs? And what\'s the cost per session?',
                    'contact': {'first_name': 'Lisa', 'last_name': 'Wilson', 'email': 'lisa.w@email.com', 'phone': '555-3691'},
                    'expected_intent': 'information_request',
                    'expected_urgency': 0.4
                }
            ]
        },
        'consulting': {
            'display_name': 'Business Consulting',
            'description': 'Strategic business consulting services',
            'sample_scenarios': [
                {
                    'name': 'Digital Transformation Project',
                    'message': 'We\'re a 50-employee manufacturing company looking to digitize our operations. Need help with strategy and implementation. Budget around $100K.',
                    'contact': {'first_name': 'Robert', 'last_name': 'Thompson', 'email': 'r.thompson@company.com', 'phone': '555-4567'},
                    'expected_intent': 'project_inquiry',
                    'expected_urgency': 0.8
                },
                {
                    'name': 'Startup Strategy Session',
                    'message': 'Early stage SaaS startup, looking for help with go-to-market strategy and investor pitch deck. What\'s your process?',
                    'contact': {'first_name': 'Emily', 'last_name': 'Zhang', 'email': 'emily@startup.co', 'phone': '555-7890'},
                    'expected_intent': 'consultation_request',
                    'expected_urgency': 0.6
                },
                {
                    'name': 'Process Optimization',
                    'message': 'Looking to improve efficiency in our customer service department. Want to explore automation and workflow improvements.',
                    'contact': {'first_name': 'James', 'last_name': 'Anderson', 'email': 'j.anderson@corp.com', 'phone': '555-1357'},
                    'expected_intent': 'efficiency_project',
                    'expected_urgency': 0.5
                }
            ]
        },
        'general': {
            'display_name': 'General Business',
            'description': 'Multi-purpose business demo',
            'sample_scenarios': [
                {
                    'name': 'Service Inquiry',
                    'message': 'I\'m interested in your services. Could you provide more information about pricing and availability?',
                    'contact': {'first_name': 'Alex', 'last_name': 'Taylor', 'email': 'alex.taylor@email.com', 'phone': '555-0987'},
                    'expected_intent': 'information_request',
                    'expected_urgency': 0.4
                },
                {
                    'name': 'Urgent Support Request',
                    'message': 'We have an urgent issue that needs immediate attention. Please call as soon as possible.',
                    'contact': {'first_name': 'Morgan', 'last_name': 'Lee', 'email': 'm.lee@business.com', 'phone': '555-6543'},
                    'expected_intent': 'support_request',
                    'expected_urgency': 0.9
                },
                {
                    'name': 'General Question',
                    'message': 'What are your business hours and location? Planning to visit next week.',
                    'contact': {'first_name': 'Jordan', 'last_name': 'Brown', 'email': 'jordan.b@email.com', 'phone': '555-2109'},
                    'expected_intent': 'general_inquiry',
                    'expected_urgency': 0.2
                }
            ]
        }
    }
    
    def __init__(self, base_dir: Path = None):
        self.base_dir = base_dir or Path(__file__).parent.parent
        self.demo_dir = self.base_dir / 'demo'
        self.scripts_dir = self.base_dir / 'scripts'
    
    def log_info(self, message: str):
        print(f"ℹ️  {message}")
    
    def log_success(self, message: str):
        print(f"✅ {message}")
    
    def log_warning(self, message: str):
        print(f"⚠️  {message}")
    
    def log_error(self, message: str):
        print(f"❌ {message}")
    
    def create_demo_scenarios_file(self, business_type: str) -> Path:
        """Create scenarios file for a business type."""
        business_info = self.BUSINESS_TYPES[business_type]
        scenarios_file = self.demo_dir / f'{business_type}_scenarios.json'
        
        scenarios_data = {
            'business_type': business_type,
            'display_name': business_info['display_name'],
            'description': business_info['description'],
            'scenarios': business_info['sample_scenarios'],
            'demo_instructions': {
                'overview': f"Demo scenarios for {business_info['display_name']}",
                'how_to_test': [
                    "1. Use the provided sample messages in your demo forms",
                    "2. Show how the AI analyzes intent and urgency",
                    "3. Demonstrate similarity detection with different customers",
                    "4. Show the Airtable integration in real-time"
                ],
                'key_features_to_highlight': [
                    "AI-powered intent classification",
                    "Automatic urgency scoring",
                    "Smart duplicate detection",
                    "Real-time CRM integration",
                    "Business-specific prompt optimization"
                ]
            }
        }
        
        with open(scenarios_file, 'w') as f:
            json.dump(scenarios_data, f, indent=2)
        
        self.log_success(f"Created scenarios file: {scenarios_file}")
        return scenarios_file
    
    def create_demo_client_config(self, business_type: str, demo_domain: str) -> Dict[str, str]:
        """Create demo client configuration."""
        client_name = f"demo-{business_type}"
        
        config = {
            'CLIENT_NAME': client_name,
            'CLIENT_DOMAIN': demo_domain,
            'BUSINESS_TYPE': business_type,
            'CLIENT_CONTACT_EMAIL': 'demo@basecamp.example.com',
            'CLIENT_TIMEZONE': 'America/New_York',
            'AIRTABLE_API_KEY': 'DEMO_API_KEY_REPLACE_WITH_REAL',
            'AIRTABLE_BASE_ID': 'DEMO_BASE_ID_REPLACE_WITH_REAL',
            'AIRTABLE_TABLE_NAME': 'Demo_Leads',
            'LETSENCRYPT_EMAIL': 'admin@basecamp.example.com'
        }
        
        return config
    
    def create_demo_airtable_base(self, business_type: str) -> Dict:
        """Create Airtable base configuration for demo."""
        business_info = self.BUSINESS_TYPES[business_type]
        
        # Basic table structure
        table_config = {
            'table_name': 'Demo_Leads',
            'fields': [
                {'name': 'Name', 'type': 'singleLineText'},
                {'name': 'Email', 'type': 'email'},
                {'name': 'Phone', 'type': 'phoneNumber'},
                {'name': 'Message', 'type': 'multilineText'},
                {'name': 'Source', 'type': 'singleSelect', 'options': ['Demo Form', 'Website Form', 'Email', 'Phone']},
                {'name': 'Intent', 'type': 'singleSelect', 'options': []},
                {'name': 'Urgency Score', 'type': 'number', 'precision': 1},
                {'name': 'Quality Score', 'type': 'number', 'precision': 1},
                {'name': 'Status', 'type': 'singleSelect', 'options': ['New', 'Contacted', 'Qualified', 'Closed']},
                {'name': 'Created', 'type': 'dateTime'},
                {'name': 'Notes', 'type': 'multilineText'}
            ]
        }
        
        # Business-specific intent options
        if business_type == 'automotive':
            table_config['fields'][5]['options'] = [
                'Service Request', 'Emergency Repair', 'Quote Request', 'Appointment', 'General Inquiry'
            ]
        elif business_type == 'medspa':
            table_config['fields'][5]['options'] = [
                'Consultation Request', 'Treatment Inquiry', 'Package Interest', 'Appointment', 'Information Request'
            ]
        elif business_type == 'consulting':
            table_config['fields'][5]['options'] = [
                'Project Inquiry', 'Consultation Request', 'Strategy Session', 'Process Optimization', 'General Inquiry'
            ]
        else:
            table_config['fields'][5]['options'] = [
                'Service Request', 'Support Request', 'Information Request', 'General Inquiry', 'Urgent Request'
            ]
        
        return table_config
    
    def create_demo_documentation(self, business_type: str, demo_domain: str) -> Path:
        """Create demo documentation and setup guide."""
        business_info = self.BUSINESS_TYPES[business_type]
        doc_file = self.demo_dir / f'{business_type}_demo_guide.md'
        
        content = f"""# baseCamp Demo: {business_info['display_name']}

## Overview
This demo showcases baseCamp's AI-powered lead intake and enrichment system specifically configured for {business_info['description']}.

## Demo URL
🌐 **Demo Instance**: https://{demo_domain}

## Business Type Configuration
- **Industry**: {business_info['display_name']}  
- **AI Optimization**: Specialized prompts for {business_type} industry
- **Lead Processing**: Industry-specific intent classification and entity extraction

## Sample Scenarios

### What to Demo
"""
        
        for i, scenario in enumerate(business_info['sample_scenarios'], 1):
            content += f"""
### {i}. {scenario['name']}

**Sample Message:**
```
{scenario['message']}
```

**Contact Info:**
- Name: {scenario['contact']['first_name']} {scenario['contact']['last_name']}
- Email: {scenario['contact']['email']}
- Phone: {scenario['contact']['phone']}

**Expected AI Analysis:**
- Intent: `{scenario['expected_intent']}`
- Urgency Score: `{scenario['expected_urgency']}`

**Demo Points:**
- Show how AI correctly identifies the intent
- Highlight industry-specific entity extraction
- Demonstrate urgency scoring based on keywords
"""
        
        content += f"""

## Demo Script

### 1. Introduction (2 minutes)
"This is baseCamp, an AI-powered lead intake system designed specifically for {business_info['description']}. It automatically processes customer inquiries, analyzes intent and urgency, and integrates directly with your CRM."

### 2. Form Submission Demo (5 minutes)
- Use one of the high-urgency scenarios (like "{business_info['sample_scenarios'][0]['name']}")
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
- Domain configured: `{demo_domain}`
- Airtable base created with demo scenarios
- SSL certificates installed

### Quick Start
```bash
# Create demo client
./scripts/provision-client.sh demo-{business_type} --domain {demo_domain} --business-type {business_type}

# Load sample scenarios (optional)
python demo/load-sample-data.py --client demo-{business_type} --scenarios demo/{business_type}_scenarios.json
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
./scripts/health-check.sh --client demo-{business_type}

# Validate configuration
python scripts/validate-production.py --client demo-{business_type}
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
*Business Type: {business_type}*
*Demo Domain: {demo_domain}*
*Created: $(date)*
"""
        
        with open(doc_file, 'w') as f:
            f.write(content)
        
        self.log_success(f"Created demo guide: {doc_file}")
        return doc_file
    
    def create_sample_data_loader(self) -> Path:
        """Create script to load sample data into demo instances."""
        loader_file = self.demo_dir / 'load-sample-data.py'
        
        content = '''#!/usr/bin/env python3
"""
Load sample scenarios into baseCamp demo instance
"""

import argparse
import json
import requests
import time
from pathlib import Path


def load_scenarios(demo_url: str, scenarios_file: Path):
    """Load scenarios via API."""
    with open(scenarios_file, 'r') as f:
        data = json.load(f)
    
    print(f"Loading {len(data['scenarios'])} scenarios for {data['display_name']}")
    
    for scenario in data['scenarios']:
        print(f"  Processing: {scenario['name']}")
        
        payload = {
            'message': scenario['message'],
            'contact': scenario['contact'],
            'source': 'demo_scenario'
        }
        
        try:
            response = requests.post(f"{demo_url}/api/v1/intake", json=payload, timeout=30)
            if response.status_code == 201:
                result = response.json()
                print(f"    ✅ Created lead: {result.get('lead_id')}")
            else:
                print(f"    ❌ Failed: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"    ❌ Error: {e}")
        
        time.sleep(2)  # Rate limiting


def main():
    parser = argparse.ArgumentParser(description='Load demo scenarios')
    parser.add_argument('--demo-url', required=True, help='Demo instance URL')
    parser.add_argument('--scenarios', required=True, type=Path, help='Scenarios JSON file')
    
    args = parser.parse_args()
    
    load_scenarios(args.demo_url, args.scenarios)


if __name__ == '__main__':
    main()
'''
        
        with open(loader_file, 'w') as f:
            f.write(content)
        
        loader_file.chmod(0o755)
        self.log_success(f"Created sample data loader: {loader_file}")
        return loader_file
    
    def setup_demo(self, business_type: str, demo_domain: str) -> Dict[str, Path]:
        """Set up complete demo for a business type."""
        self.log_info(f"Setting up demo for {business_type}: {demo_domain}")
        
        # Create demo directory
        self.demo_dir.mkdir(exist_ok=True)
        
        # Create all demo files
        scenarios_file = self.create_demo_scenarios_file(business_type)
        doc_file = self.create_demo_documentation(business_type, demo_domain)
        
        # Create sample data loader if it doesn't exist
        loader_file = self.demo_dir / 'load-sample-data.py'
        if not loader_file.exists():
            self.create_sample_data_loader()
        
        # Create Airtable configuration
        airtable_config = self.create_demo_airtable_base(business_type)
        airtable_file = self.demo_dir / f'{business_type}_airtable_config.json'
        with open(airtable_file, 'w') as f:
            json.dump(airtable_config, f, indent=2)
        
        self.log_success(f"Demo setup completed for {business_type}")
        
        return {
            'scenarios': scenarios_file,
            'documentation': doc_file,
            'airtable_config': airtable_file
        }
    
    def interactive_setup(self):
        """Interactive demo setup."""
        print("🎯 baseCamp Demo Setup - Interactive Mode")
        print("=" * 50)
        
        # Select business type
        print("\\nAvailable business types:")
        for i, (key, info) in enumerate(self.BUSINESS_TYPES.items(), 1):
            print(f"  {i}. {key}: {info['display_name']}")
        
        while True:
            try:
                choice = input("\\nSelect business type (1-4): ").strip()
                if choice.isdigit() and 1 <= int(choice) <= len(self.BUSINESS_TYPES):
                    business_type = list(self.BUSINESS_TYPES.keys())[int(choice) - 1]
                    break
                else:
                    print("Invalid choice. Please enter 1-4.")
            except (ValueError, KeyboardInterrupt):
                print("\\nSetup cancelled.")
                return
        
        # Get demo domain
        while True:
            demo_domain = input(f"\\nEnter demo domain for {business_type} (e.g., demo-{business_type}.example.com): ").strip()
            if demo_domain:
                break
            print("Domain is required.")
        
        # Confirm setup
        print(f"\\n📋 Demo Setup Summary:")
        print(f"  Business Type: {business_type}")
        print(f"  Demo Domain: {demo_domain}")
        print(f"  Scenarios: {len(self.BUSINESS_TYPES[business_type]['sample_scenarios'])}")
        
        confirm = input("\\nProceed with setup? (y/N): ").strip().lower()
        if confirm != 'y':
            print("Setup cancelled.")
            return
        
        # Run setup
        files = self.setup_demo(business_type, demo_domain)
        
        # Print next steps
        print(f"\\n🎉 Demo setup completed!")
        print(f"\\n📁 Generated files:")
        for file_type, file_path in files.items():
            print(f"   • {file_type}: {file_path}")
        
        print(f"\\n📝 Next steps:")
        print(f"   1. Review the demo guide: {files['documentation']}")
        print(f"   2. Set up Airtable base using: {files['airtable_config']}")
        print(f"   3. Deploy demo client: scripts/provision-client.sh demo-{business_type} --domain {demo_domain} --business-type {business_type}")
        print(f"   4. Load sample data: demo/load-sample-data.py --demo-url https://{demo_domain} --scenarios {files['scenarios']}")


def main():
    parser = argparse.ArgumentParser(description='Setup baseCamp demo instances')
    parser.add_argument('--business-type', choices=['automotive', 'medspa', 'consulting', 'general'],
                       help='Business type for demo')
    parser.add_argument('--demo-domain', help='Domain for demo instance')
    parser.add_argument('--all-business-types', action='store_true',
                       help='Create demos for all business types')
    parser.add_argument('--interactive', action='store_true',
                       help='Interactive setup mode')
    parser.add_argument('--base-dir', type=Path, help='Base directory (default: auto-detect)')
    
    args = parser.parse_args()
    
    demo_setup = DemoSetup(args.base_dir)
    
    if args.interactive:
        demo_setup.interactive_setup()
    elif args.all_business_types:
        for business_type in demo_setup.BUSINESS_TYPES.keys():
            demo_domain = f"demo-{business_type}.basecamp.example.com"
            demo_setup.setup_demo(business_type, demo_domain)
    elif args.business_type and args.demo_domain:
        demo_setup.setup_demo(args.business_type, args.demo_domain)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()