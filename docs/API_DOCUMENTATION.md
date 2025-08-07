# baseCamp API Documentation

Complete API reference for integrating with baseCamp's AI-powered lead processing system.

## 📋 Table of Contents

1. [Overview](#overview)
2. [Authentication](#authentication)  
3. [API Endpoints](#api-endpoints)
4. [Data Models](#data-models)
5. [Integration Examples](#integration-examples)
6. [Error Handling](#error-handling)
7. [Rate Limiting](#rate-limiting)
8. [Webhooks](#webhooks)
9. [SDKs & Libraries](#sdks--libraries)

## Overview

### Base URL
```
https://your-client-domain.com/api/v1
```

### API Features
- ✅ **Lead Intake Processing** - Submit leads for AI analysis
- ✅ **Intelligent Lead Enrichment** - AI-powered intent classification and urgency scoring  
- ✅ **Duplicate Detection** - Smart similarity search with contact-based exclusion
- ✅ **CRM Integration** - Automatic Airtable synchronization
- ✅ **Real-time Processing** - Background processing for fast response times
- ✅ **Business-type Optimization** - Industry-specific prompt templates

### Content Type
All API endpoints accept and return JSON data:
```
Content-Type: application/json
```

### Response Format
All responses follow a consistent structure:
```json
{
  "success": true,
  "data": { ... },
  "errors": [],
  "metadata": {
    "timestamp": "2024-01-15T10:30:00Z",
    "version": "1.0.0",
    "request_id": "req_123456"
  }
}
```

## Authentication

### API Key Authentication (Optional)
If enabled, include your API key in the header:
```bash
curl -H "X-API-Key: your-api-key" https://client.example.com/api/v1/health
```

### Rate Limiting
- **Default**: 30 requests per minute per IP address
- **Burst**: 10 additional requests allowed
- **Headers**: Rate limit status included in response headers

```http
X-RateLimit-Limit: 30
X-RateLimit-Remaining: 25  
X-RateLimit-Reset: 1642248000
```

## API Endpoints

### Health & Status

#### GET /health
Check system health and status.

**Response:**
```json
{
  "success": true,
  "data": {
    "status": "healthy",
    "services": {
      "api": "healthy",
      "llm": "healthy", 
      "vector_db": "healthy",
      "crm": "healthy"
    },
    "version": "1.0.0",
    "uptime": 86400
  }
}
```

#### GET /config (Development Only)
Get configuration information (disabled in production).

---

### Lead Intake API

#### POST /intake
Submit a new lead for processing.

**Request Body:**
```json
{
  "message": "My 2019 Honda Civic makes a grinding noise when I brake. Can someone look at it today?",
  "contact": {
    "first_name": "Sarah",
    "last_name": "Johnson", 
    "email": "sarah.j@email.com",
    "phone": "555-0123"
  },
  "source": "web_form",
  "metadata": {
    "page_url": "https://client.com/contact",
    "user_agent": "Mozilla/5.0...",
    "referrer": "https://google.com"
  }
}
```

**Response (201 Created):**
```json
{
  "success": true,
  "data": {
    "lead_id": "lead_67890",
    "status": "processing",
    "message": "Lead submitted successfully",
    "estimated_processing_time": "5-10 seconds"
  }
}
```

**cURL Example:**
```bash
curl -X POST https://client.example.com/api/v1/intake \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Need brake repair for my Honda Civic",
    "contact": {
      "first_name": "John",
      "last_name": "Doe",
      "email": "john@example.com",
      "phone": "555-0123"
    },
    "source": "web_form"
  }'
```

#### POST /intake/batch
Process multiple leads in a single request (up to 50 leads).

**Request Body:**
```json
{
  "leads": [
    {
      "message": "Need oil change for my Toyota",
      "contact": {
        "first_name": "Alice",
        "last_name": "Smith",
        "email": "alice@example.com"
      },
      "source": "web_form"
    },
    {
      "message": "Check engine light is on",
      "contact": {
        "first_name": "Bob", 
        "last_name": "Wilson",
        "email": "bob@example.com"
      },
      "source": "phone_call"
    }
  ]
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "batch_id": "batch_12345",
    "total_leads": 2,
    "accepted": 2,
    "rejected": 0,
    "lead_ids": ["lead_67891", "lead_67892"]
  }
}
```

#### POST /intake/check-similar
Check for similar leads before submission.

**Request Body:**
```json
{
  "message": "My brake pads need replacement",
  "contact": {
    "first_name": "Jane",
    "last_name": "Doe",
    "email": "jane@example.com"
  }
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "has_similar": true,
    "similar_leads": [
      {
        "lead_id": "lead_12345",
        "similarity_score": 0.85,
        "contact_match": false,
        "message_preview": "Brake repair needed for 2020 Honda...",
        "created_at": "2024-01-14T15:30:00Z"
      }
    ],
    "duplicate_risk": "medium"
  }
}
```

#### GET /intake/health
Check intake service health.

**Response:**
```json
{
  "success": true,
  "data": {
    "intake_status": "operational",
    "processing_queue": 3,
    "average_processing_time": "8.5s",
    "last_processed": "2024-01-15T10:29:45Z"
  }
}
```

---

### Lead Management API

#### GET /leads
List and search leads with pagination.

**Query Parameters:**
- `limit` (int): Number of results per page (default: 50, max: 100)
- `offset` (int): Number of results to skip (default: 0)
- `status` (string): Filter by status (`raw`, `processing`, `enriched`, `synced`, `failed`)
- `source` (string): Filter by source (`web_form`, `email`, `phone_call`, etc.)
- `business_type` (string): Filter by business type
- `created_after` (ISO date): Filter by creation date
- `created_before` (ISO date): Filter by creation date  
- `search` (string): Search in message content
- `sort` (string): Sort field (`created_at`, `urgency_score`, `quality_score`)
- `order` (string): Sort order (`asc`, `desc`)

**Request:**
```bash
curl "https://client.example.com/api/v1/leads?limit=10&status=enriched&sort=created_at&order=desc"
```

**Response:**
```json
{
  "success": true,
  "data": {
    "leads": [
      {
        "lead_id": "lead_12345",
        "message": "Need brake repair urgently...",
        "contact": {
          "first_name": "Sarah",
          "last_name": "Johnson",
          "email": "sarah@example.com",
          "phone": "555-0123"
        },
        "ai_analysis": {
          "intent": "appointment_request",
          "urgency_score": 0.9,
          "quality_score": 85,
          "entities": {
            "vehicle": "2019 Honda Civic",
            "service_type": "brake_repair",
            "urgency_indicators": ["urgently", "today"]
          },
          "confidence": 0.92
        },
        "status": "synced",
        "source": "web_form",
        "created_at": "2024-01-15T10:15:00Z",
        "updated_at": "2024-01-15T10:15:10Z"
      }
    ],
    "pagination": {
      "total": 150,
      "limit": 10,
      "offset": 0,
      "has_more": true,
      "next_cursor": "cursor_abc123"
    }
  }
}
```

#### GET /leads/{lead_id}
Get detailed information for a specific lead.

**Response:**
```json
{
  "success": true,
  "data": {
    "lead_id": "lead_12345",
    "message": "My 2019 Honda Civic makes a grinding noise when I brake...",
    "contact": {
      "first_name": "Sarah",
      "last_name": "Johnson",
      "email": "sarah@example.com", 
      "phone": "555-0123"
    },
    "ai_analysis": {
      "intent": "appointment_request",
      "intent_confidence": 0.92,
      "urgency_score": 0.9,
      "quality_score": 85,
      "entities": {
        "vehicle": "2019 Honda Civic",
        "service_type": "brake_repair",
        "urgency_indicators": ["grinding noise", "today"],
        "contact_preferences": ["phone"]
      },
      "summary": "Customer has urgent brake issue with grinding noise, needs same-day service",
      "recommended_actions": [
        "Schedule emergency appointment",
        "Call customer immediately", 
        "Prepare brake inspection"
      ]
    },
    "processing_details": {
      "processing_time": "5.2s",
      "llm_model": "mistral:latest",
      "prompt_template": "automotive_v1.2",
      "vector_similarity_check": true,
      "duplicate_score": 0.23
    },
    "crm_sync": {
      "airtable_record_id": "rec123456789",
      "sync_status": "completed", 
      "sync_time": "2024-01-15T10:15:10Z",
      "retry_count": 0
    },
    "metadata": {
      "source": "web_form",
      "page_url": "https://client.com/contact",
      "user_agent": "Mozilla/5.0...",
      "ip_address": "192.168.1.100",
      "session_id": "sess_abc123"
    },
    "status": "synced",
    "created_at": "2024-01-15T10:15:00Z",
    "updated_at": "2024-01-15T10:15:10Z"
  }
}
```

#### PUT /leads/{lead_id}
Update lead information or status.

**Request Body:**
```json
{
  "status": "contacted", 
  "notes": "Called customer, scheduled appointment for tomorrow",
  "metadata": {
    "appointment_scheduled": "2024-01-16T09:00:00Z",
    "assigned_technician": "John Smith"
  }
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "lead_id": "lead_12345",
    "status": "contacted",
    "updated_at": "2024-01-15T11:30:00Z"
  }
}
```

#### DELETE /leads/{lead_id}
Delete a lead from the system.

**Response:**
```json
{
  "success": true,
  "data": {
    "message": "Lead deleted successfully",
    "deleted_at": "2024-01-15T12:00:00Z"
  }
}
```

#### GET /leads/{lead_id}/similar
Find leads similar to the specified lead.

**Query Parameters:**
- `limit` (int): Number of results (default: 10, max: 50)
- `threshold` (float): Similarity threshold (default: 0.7, range: 0.0-1.0)
- `exclude_same_contact` (bool): Exclude leads from same contact (default: true)

**Response:**
```json
{
  "success": true,
  "data": {
    "similar_leads": [
      {
        "lead_id": "lead_67890",
        "similarity_score": 0.85,
        "contact_match": false,
        "message_preview": "Brake pads making noise in my 2018 Honda Accord...",
        "ai_analysis": {
          "intent": "service_request",
          "urgency_score": 0.7
        },
        "created_at": "2024-01-14T14:20:00Z"
      }
    ],
    "search_params": {
      "threshold": 0.7,
      "exclude_same_contact": true,
      "total_candidates": 1250,
      "matches_found": 1
    }
  }
}
```

#### POST /leads/export
Export leads in various formats.

**Request Body:**
```json
{
  "format": "csv",
  "filters": {
    "status": ["enriched", "synced"],
    "created_after": "2024-01-01T00:00:00Z",
    "business_type": "automotive"
  },
  "fields": [
    "lead_id",
    "contact.first_name",
    "contact.last_name", 
    "contact.email",
    "ai_analysis.intent",
    "ai_analysis.urgency_score",
    "created_at"
  ]
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "export_id": "export_abc123",
    "format": "csv",
    "total_records": 1250,
    "estimated_size": "2.5MB",
    "download_url": "https://client.example.com/api/v1/exports/export_abc123",
    "expires_at": "2024-01-16T10:15:00Z"
  }
}
```

#### GET /leads/stats/summary
Get aggregate statistics for leads.

**Query Parameters:**
- `period` (string): Time period (`day`, `week`, `month`, `year`)
- `start_date` (ISO date): Start date for statistics
- `end_date` (ISO date): End date for statistics

**Response:**
```json
{
  "success": true,
  "data": {
    "period": "month",
    "start_date": "2024-01-01T00:00:00Z",
    "end_date": "2024-01-31T23:59:59Z",
    "totals": {
      "leads_submitted": 1250,
      "leads_processed": 1248,
      "leads_synced": 1240,
      "leads_failed": 2
    },
    "averages": {
      "processing_time": "6.8s",
      "urgency_score": 0.65,
      "quality_score": 78.5
    },
    "intents": {
      "service_request": 520,
      "appointment_request": 380,
      "quote_request": 220,
      "general_inquiry": 128
    },
    "sources": {
      "web_form": 890,
      "phone_call": 210,
      "email": 150
    },
    "daily_breakdown": [
      {
        "date": "2024-01-01",
        "leads": 42,
        "avg_urgency": 0.6
      }
    ]
  }
}
```

---

## Data Models

### LeadInput
Input data for lead submission.

```json
{
  "message": "string (required, 1-10000 chars)",
  "contact": {
    "first_name": "string (required, 1-50 chars)",
    "last_name": "string (optional, 1-50 chars)",
    "email": "string (optional, valid email)",
    "phone": "string (optional, valid phone number)"
  },
  "source": "enum (web_form, email, phone_call, chat, api)",
  "business_type": "enum (automotive, medspa, consulting, general)", 
  "metadata": {
    "page_url": "string (optional)",
    "user_agent": "string (optional)",
    "referrer": "string (optional)",
    "session_id": "string (optional)",
    "custom_fields": "object (optional)"
  }
}
```

### EnrichedLead
Processed lead with AI analysis.

```json
{
  "lead_id": "string (unique identifier)",
  "message": "string (original message)",
  "contact": "ContactInfo object",
  "ai_analysis": {
    "intent": "string (classified intent)",
    "intent_confidence": "float (0.0-1.0)",
    "urgency_score": "float (0.0-1.0)", 
    "quality_score": "integer (0-100)",
    "entities": "object (extracted entities)",
    "summary": "string (AI-generated summary)",
    "recommended_actions": ["array of strings"]
  },
  "processing_details": {
    "processing_time": "string (duration)",
    "llm_model": "string (model used)",
    "prompt_template": "string (template version)",
    "vector_similarity_check": "boolean",
    "duplicate_score": "float (0.0-1.0)"
  },
  "crm_sync": {
    "airtable_record_id": "string (optional)",
    "sync_status": "enum (pending, completed, failed)",
    "sync_time": "ISO datetime (optional)",
    "retry_count": "integer"
  },
  "status": "enum (raw, processing, enriched, synced, failed)",
  "source": "enum (source type)",
  "metadata": "object (request metadata)",
  "created_at": "ISO datetime",
  "updated_at": "ISO datetime"
}
```

### AIAnalysis
AI processing results.

```json
{
  "intent": "string (primary intent classification)",
  "intent_confidence": "float (confidence score 0.0-1.0)",
  "urgency_score": "float (urgency level 0.0-1.0)",
  "quality_score": "integer (lead quality 0-100)",
  "entities": {
    "vehicle": "string (for automotive)",
    "service_type": "string",
    "urgency_indicators": ["array of detected phrases"],
    "contact_preferences": ["array of preferences"],
    "budget_indicators": ["array of budget-related text"],
    "timeline_indicators": ["array of timing phrases"]
  },
  "summary": "string (AI-generated summary)",
  "recommended_actions": ["array of suggested next steps"],
  "confidence": "float (overall confidence 0.0-1.0)"
}
```

### ContactInfo
Contact information with validation.

```json
{
  "first_name": "string (1-50 chars)",
  "last_name": "string (optional, 1-50 chars)",
  "full_name": "string (computed full name)", 
  "email": "string (validated email format)",
  "phone": "string (validated phone number)",
  "is_valid_email": "boolean",
  "is_valid_phone": "boolean"
}
```

## Integration Examples

### JavaScript (Frontend Form)

```html
<!DOCTYPE html>
<html>
<head>
    <title>Contact Form</title>
</head>
<body>
    <form id="contact-form">
        <input type="text" name="first_name" placeholder="First Name" required>
        <input type="text" name="last_name" placeholder="Last Name">
        <input type="email" name="email" placeholder="Email">
        <input type="tel" name="phone" placeholder="Phone">
        <textarea name="message" placeholder="Describe your needs..." required></textarea>
        <button type="submit">Submit</button>
    </form>

    <script>
        document.getElementById('contact-form').addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const formData = new FormData(e.target);
            const payload = {
                message: formData.get('message'),
                contact: {
                    first_name: formData.get('first_name'),
                    last_name: formData.get('last_name'),
                    email: formData.get('email'),
                    phone: formData.get('phone')
                },
                source: 'web_form',
                metadata: {
                    page_url: window.location.href,
                    user_agent: navigator.userAgent,
                    referrer: document.referrer
                }
            };

            try {
                const response = await fetch('/api/v1/intake', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(payload)
                });

                const result = await response.json();
                
                if (result.success) {
                    alert('Thank you! Your request has been submitted.');
                    e.target.reset();
                } else {
                    alert('Error: ' + result.errors.join(', '));
                }
            } catch (error) {
                alert('Network error. Please try again.');
                console.error('Submission error:', error);
            }
        });
    </script>
</body>
</html>
```

### Python Client

```python
import requests
import json
from typing import Dict, List, Optional

class BaseCampClient:
    def __init__(self, base_url: str, api_key: Optional[str] = None):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        
        if api_key:
            self.session.headers.update({'X-API-Key': api_key})
        
        self.session.headers.update({'Content-Type': 'application/json'})
    
    def submit_lead(self, message: str, contact: Dict, source: str = 'api', 
                   metadata: Optional[Dict] = None) -> Dict:
        """Submit a new lead for processing."""
        payload = {
            'message': message,
            'contact': contact,
            'source': source,
            'metadata': metadata or {}
        }
        
        response = self.session.post(f'{self.base_url}/api/v1/intake', 
                                   json=payload)
        response.raise_for_status()
        return response.json()
    
    def get_lead(self, lead_id: str) -> Dict:
        """Get detailed lead information."""
        response = self.session.get(f'{self.base_url}/api/v1/leads/{lead_id}')
        response.raise_for_status()
        return response.json()
    
    def list_leads(self, limit: int = 50, **filters) -> Dict:
        """List leads with optional filtering."""
        params = {'limit': limit, **filters}
        response = self.session.get(f'{self.base_url}/api/v1/leads', 
                                  params=params)
        response.raise_for_status()
        return response.json()
    
    def check_similar(self, message: str, contact: Dict) -> Dict:
        """Check for similar leads."""
        payload = {'message': message, 'contact': contact}
        response = self.session.post(f'{self.base_url}/api/v1/intake/check-similar',
                                   json=payload)
        response.raise_for_status()
        return response.json()
    
    def health_check(self) -> Dict:
        """Check system health."""
        response = self.session.get(f'{self.base_url}/api/v1/health')
        response.raise_for_status()
        return response.json()

# Usage example
client = BaseCampClient('https://client.example.com')

# Submit a lead
result = client.submit_lead(
    message="Need brake repair for my Honda Civic",
    contact={
        'first_name': 'John',
        'last_name': 'Doe', 
        'email': 'john@example.com',
        'phone': '555-0123'
    },
    source='api'
)

print(f"Lead submitted: {result['data']['lead_id']}")

# Check system health
health = client.health_check()
print(f"System status: {health['data']['status']}")

# List recent leads
leads = client.list_leads(limit=10, sort='created_at', order='desc')
print(f"Found {len(leads['data']['leads'])} recent leads")
```

### Node.js Integration

```javascript
const axios = require('axios');

class BaseCampClient {
    constructor(baseUrl, apiKey = null) {
        this.baseUrl = baseUrl.replace(/\/+$/, '');
        this.axios = axios.create({
            baseURL: `${this.baseUrl}/api/v1`,
            headers: {
                'Content-Type': 'application/json',
                ...(apiKey && { 'X-API-Key': apiKey })
            }
        });
    }

    async submitLead(message, contact, source = 'api', metadata = {}) {
        try {
            const response = await this.axios.post('/intake', {
                message,
                contact,
                source,
                metadata
            });
            return response.data;
        } catch (error) {
            throw new Error(`Lead submission failed: ${error.response?.data?.errors || error.message}`);
        }
    }

    async getLead(leadId) {
        try {
            const response = await this.axios.get(`/leads/${leadId}`);
            return response.data;
        } catch (error) {
            throw new Error(`Get lead failed: ${error.response?.data?.errors || error.message}`);
        }
    }

    async listLeads(options = {}) {
        try {
            const response = await this.axios.get('/leads', { params: options });
            return response.data;
        } catch (error) {
            throw new Error(`List leads failed: ${error.response?.data?.errors || error.message}`);
        }
    }

    async checkSimilar(message, contact) {
        try {
            const response = await this.axios.post('/intake/check-similar', {
                message,
                contact
            });
            return response.data;
        } catch (error) {
            throw new Error(`Similarity check failed: ${error.response?.data?.errors || error.message}`);
        }
    }

    async healthCheck() {
        try {
            const response = await this.axios.get('/health');
            return response.data;
        } catch (error) {
            throw new Error(`Health check failed: ${error.response?.data?.errors || error.message}`);
        }
    }
}

// Usage example
async function main() {
    const client = new BaseCampClient('https://client.example.com');

    try {
        // Submit a lead
        const result = await client.submitLead(
            "My car's check engine light is on and it's making weird noises",
            {
                first_name: 'Sarah',
                last_name: 'Johnson',
                email: 'sarah@example.com',
                phone: '555-0123'
            },
            'api'
        );

        console.log(`Lead submitted: ${result.data.lead_id}`);

        // Check for similar leads
        const similarCheck = await client.checkSimilar(
            "Check engine light problems",
            { first_name: 'Bob', email: 'bob@example.com' }
        );

        console.log(`Similar leads found: ${similarCheck.data.similar_leads.length}`);

        // Get health status
        const health = await client.healthCheck();
        console.log(`System status: ${health.data.status}`);

    } catch (error) {
        console.error('API Error:', error.message);
    }
}

main();
```

## Error Handling

### Error Response Format
```json
{
  "success": false,
  "data": null,
  "errors": [
    {
      "code": "VALIDATION_ERROR",
      "message": "Invalid email format",
      "field": "contact.email",
      "details": {
        "provided": "invalid-email",
        "expected": "valid email address"
      }
    }
  ],
  "metadata": {
    "timestamp": "2024-01-15T10:30:00Z",
    "request_id": "req_123456"
  }
}
```

### HTTP Status Codes
- **200 OK**: Request successful
- **201 Created**: Resource created successfully
- **400 Bad Request**: Invalid request data
- **401 Unauthorized**: API key required or invalid
- **403 Forbidden**: Access denied
- **404 Not Found**: Resource not found
- **422 Unprocessable Entity**: Validation errors
- **429 Too Many Requests**: Rate limit exceeded
- **500 Internal Server Error**: Server error
- **503 Service Unavailable**: Service temporarily unavailable

### Common Error Codes

#### Validation Errors
- `VALIDATION_ERROR`: Input validation failed
- `REQUIRED_FIELD_MISSING`: Required field not provided
- `INVALID_FORMAT`: Field format invalid
- `VALUE_OUT_OF_RANGE`: Value outside allowed range

#### Processing Errors  
- `PROCESSING_FAILED`: Lead processing failed
- `LLM_SERVICE_UNAVAILABLE`: AI analysis service down
- `CRM_SYNC_FAILED`: Airtable synchronization failed
- `DUPLICATE_DETECTION_FAILED`: Similarity check failed

#### Rate Limiting
- `RATE_LIMIT_EXCEEDED`: Too many requests
- `QUOTA_EXCEEDED`: Daily/monthly quota exceeded

#### System Errors
- `INTERNAL_ERROR`: Unexpected server error
- `SERVICE_UNAVAILABLE`: Service temporarily down
- `TIMEOUT`: Request timeout

### Error Handling Best Practices

```python
import time
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

def create_resilient_client():
    session = requests.Session()
    
    # Configure retries
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504]
    )
    
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    return session

def submit_lead_with_retry(client, payload, max_retries=3):
    for attempt in range(max_retries):
        try:
            response = client.post('/api/v1/intake', json=payload)
            
            if response.status_code == 201:
                return response.json()
            elif response.status_code == 429:
                # Rate limited - wait and retry
                wait_time = int(response.headers.get('Retry-After', 60))
                print(f"Rate limited. Waiting {wait_time} seconds...")
                time.sleep(wait_time)
                continue
            else:
                # Other error
                error_data = response.json()
                raise Exception(f"API Error: {error_data['errors']}")
                
        except requests.RequestException as e:
            if attempt == max_retries - 1:
                raise
            print(f"Request failed, retrying... (attempt {attempt + 1})")
            time.sleep(2 ** attempt)  # Exponential backoff
```

## Rate Limiting

### Default Limits
- **Intake API**: 30 requests per minute per IP
- **Query APIs**: 60 requests per minute per IP  
- **Export APIs**: 5 requests per hour per IP
- **Batch APIs**: 10 requests per hour per IP

### Rate Limit Headers
```http
X-RateLimit-Limit: 30
X-RateLimit-Remaining: 25
X-RateLimit-Reset: 1642248000
X-RateLimit-Retry-After: 60
```

### Handling Rate Limits
```javascript
async function makeApiRequest(url, options) {
    const response = await fetch(url, options);
    
    if (response.status === 429) {
        const retryAfter = response.headers.get('Retry-After');
        console.log(`Rate limited. Retry after ${retryAfter} seconds`);
        
        await new Promise(resolve => 
            setTimeout(resolve, retryAfter * 1000)
        );
        
        return makeApiRequest(url, options); // Retry
    }
    
    return response;
}
```

## Webhooks

### Webhook Events
- `lead.created` - New lead submitted
- `lead.processed` - AI analysis completed
- `lead.synced` - CRM synchronization completed  
- `lead.failed` - Processing failed
- `system.health_alert` - System health issue

### Webhook Payload Example
```json
{
  "event": "lead.processed",
  "timestamp": "2024-01-15T10:15:10Z",
  "data": {
    "lead_id": "lead_12345",
    "status": "enriched",
    "ai_analysis": {
      "intent": "appointment_request",
      "urgency_score": 0.9,
      "quality_score": 85
    }
  },
  "metadata": {
    "webhook_id": "wh_abc123",
    "signature": "sha256=abc123..."
  }
}
```

### Webhook Configuration
Contact your baseCamp administrator to configure webhooks for your client instance.

## SDKs & Libraries

### Official SDKs
- **JavaScript/Node.js**: `@basecamp/api-client`
- **Python**: `basecamp-client`  
- **PHP**: `basecamp/api-client`

### Installation
```bash
# JavaScript/Node.js
npm install @basecamp/api-client

# Python  
pip install basecamp-client

# PHP
composer require basecamp/api-client
```

### Community SDKs
- **Ruby**: `basecamp-ruby`
- **Go**: `go-basecamp`
- **Java**: `basecamp-java-sdk`

---

## Support & Resources

### Documentation
- 📚 **API Docs**: https://docs.basecamp.example.com/api
- 🔗 **Integration Guide**: https://docs.basecamp.example.com/integration  
- 📖 **Best Practices**: https://docs.basecamp.example.com/best-practices

### Support Channels  
- 📧 **Email**: api-support@basecamp.example.com
- 💬 **Chat**: Available in client dashboard
- 🐛 **Issues**: https://github.com/your-org/basecamp-client-issues

### Testing
- 🧪 **Sandbox Environment**: https://sandbox.basecamp.example.com
- 📊 **API Explorer**: https://client.example.com/api/docs
- 🔍 **Postman Collection**: Available in documentation

---

*API Version: v1.0*  
*Last Updated: January 2025*