# baseCamp - System Requirements

## Functional Requirements

### FR1: Lead Intake Processing
- **FR1.1**: Accept lead submissions from multiple sources (web forms, API calls, chat interfaces)
- **FR1.2**: Validate and sanitize incoming lead data
- **FR1.3**: Store original lead data with timestamp and source attribution
- **FR1.4**: Support various input formats (JSON, form data, plain text)
- **FR1.5**: Handle contact information (name, email, phone, address)

### FR2: AI-Powered Lead Enrichment
- **FR2.1**: Analyze lead messages using local LLM (Ollama)
- **FR2.2**: Extract key entities (service type, urgency indicators, contact preferences)
- **FR2.3**: Classify lead intent (service request, inquiry, complaint, quote request)
- **FR2.4**: Generate urgency score (0.0-1.0 scale)
- **FR2.5**: Calculate lead quality score based on completeness and intent
- **FR2.6**: Support configurable prompt templates for different business types

### FR3: Duplicate Detection
- **FR3.1**: Generate semantic embeddings for lead content
- **FR3.2**: Perform similarity search against existing leads
- **FR3.3**: Flag potential duplicates above configurable threshold (default: 0.85)
- **FR3.4**: Provide similarity scores and match details
- **FR3.5**: Allow manual override of duplicate detection

### FR4: CRM Integration
- **FR4.1**: Sync enriched leads to Airtable automatically
- **FR4.2**: Map internal lead structure to Airtable schema
- **FR4.3**: Handle Airtable API rate limits and retries
- **FR4.4**: Support bidirectional sync for lead status updates
- **FR4.5**: Maintain mapping between internal IDs and Airtable record IDs

### FR5: Lead Management API
- **FR5.1**: RESTful API for CRUD operations on leads
- **FR5.2**: Search and filter leads by various criteria
- **FR5.3**: Bulk operations for lead processing
- **FR5.4**: Export leads in multiple formats (JSON, CSV)
- **FR5.5**: API authentication and authorization

### FR6: System Monitoring
- **FR6.1**: Health check endpoint for system status
- **FR6.2**: Monitor LLM service availability
- **FR6.3**: Track processing metrics (throughput, latency, error rates)
- **FR6.4**: Log significant events and errors
- **FR6.5**: Alert on system failures or degraded performance

## Non-Functional Requirements

### NFR1: Performance
- **NFR1.1**: Process lead intake within 5 seconds (95th percentile)
- **NFR1.2**: Support concurrent processing of up to 100 leads
- **NFR1.3**: Vector similarity search completes within 2 seconds
- **NFR1.4**: API response time under 3 seconds for CRUD operations
- **NFR1.5**: System startup time under 30 seconds

### NFR2: Scalability
- **NFR2.1**: Handle 10,000 leads per day with current architecture
- **NFR2.2**: ChromaDB collections scale to 100,000+ embeddings
- **NFR2.3**: Horizontal scaling support via containerization
- **NFR2.4**: Database performance maintained with 50,000+ records
- **NFR2.5**: Memory usage under 2GB for typical workloads

### NFR3: Reliability
- **NFR3.1**: System uptime of 99.5% during business hours
- **NFR3.2**: Graceful degradation when LLM service unavailable
- **NFR3.3**: Data persistence guarantees (no lead data loss)
- **NFR3.4**: Automatic retry mechanisms for external API calls
- **NFR3.5**: Transaction rollback on processing failures

### NFR4: Security
- **NFR4.1**: API authentication via API keys or OAuth
- **NFR4.2**: Rate limiting to prevent abuse
- **NFR4.3**: Input validation and sanitization
- **NFR4.4**: Secure storage of API keys and credentials
- **NFR4.5**: HTTPS-only communication in production

### NFR5: Usability
- **NFR5.1**: RESTful API design following OpenAPI standards
- **NFR5.2**: Comprehensive API documentation
- **NFR5.3**: Clear error messages and status codes
- **NFR5.4**: Consistent JSON response formats
- **NFR5.5**: Easy configuration via environment variables

### NFR6: Maintainability
- **NFR6.1**: Modular architecture with clear service boundaries
- **NFR6.2**: Comprehensive test coverage (>80%)
- **NFR6.3**: Type hints and documentation for all public APIs
- **NFR6.4**: Structured logging for debugging
- **NFR6.5**: Configuration externalization

## Integration Requirements

### IR1: Ollama LLM Service
- **IR1.1**: Compatible with Ollama API v1.0+
- **IR1.2**: Support for Mistral, Llama, and similar models
- **IR1.3**: Configurable model selection via environment variables
- **IR1.4**: Timeout handling for LLM requests (default: 30 seconds)
- **IR1.5**: Fallback behavior when LLM unavailable

### IR2: ChromaDB Vector Database
- **IR2.1**: ChromaDB version 0.4.0+ compatibility
- **IR2.2**: Persistent storage configuration
- **IR2.3**: Custom embedding function support
- **IR2.4**: Collection management and indexing
- **IR2.5**: Metadata filtering capabilities

### IR3: Airtable CRM Integration
- **IR3.1**: Airtable API v0.3.0+ support
- **IR3.2**: Dynamic base and table configuration
- **IR3.3**: Field mapping configuration
- **IR3.4**: Webhook support for real-time updates
- **IR3.5**: Batch operations for bulk sync

## Infrastructure Requirements

### Hardware Requirements
- **CPU**: 4+ cores recommended for concurrent processing
- **RAM**: 4GB minimum, 8GB recommended
- **Storage**: 10GB minimum for application and data
- **Network**: Stable internet connection for Airtable sync

### Software Requirements
- **OS**: Linux, macOS, or Windows with Docker support
- **Python**: 3.9+ with pip package manager
- **Docker**: 20.10+ for containerized deployment
- **Ollama**: Latest version with model support

### Deployment Requirements
- **Environment**: Support for development, staging, and production
- **Configuration**: Environment-based configuration management
- **Monitoring**: Health checks and basic metrics collection
- **Backup**: Regular backup of ChromaDB and configuration data
- **Updates**: Rolling update capability with zero downtime

## Compliance and Data Requirements

### Data Privacy
- **DP1**: Secure handling of personally identifiable information (PII)
- **DP2**: Data retention policies configurable by business needs
- **DP3**: Audit trail for data access and modifications
- **DP4**: Support for data deletion requests

### Business Continuity
- **BC1**: Regular automated backups of lead data
- **BC2**: Disaster recovery procedures documented
- **BC3**: Data export capabilities for migration
- **BC4**: System restore procedures tested quarterly