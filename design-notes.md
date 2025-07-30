# baseCamp - Technical Design Notes

## 📊 Implementation Status

**✅ IMPLEMENTED**: 
- System architecture foundation
- FastAPI application with health endpoints
- Pydantic settings with comprehensive configuration
- Docker containerization with Ollama integration
- Development tooling and quality checks

**🚧 READY FOR IMPLEMENTATION**:
- Service layer interfaces defined
- Data models architecture planned
- API endpoint structure designed
- Error handling patterns established

**📋 PLANNED**:
- AI service implementations
- Database integrations
- Business logic and processing pipeline

## System Architecture Overview

### High-Level Architecture
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Client Apps   │    │   Web Forms     │    │   API Clients   │
│   (Mobile/Web)  │    │   (Embedded)    │    │   (Zapier/etc)  │
└─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘
          │                      │                      │
          └──────────────────────┼──────────────────────┘
                                 │
                    ┌─────────────┴─────────────┐
                    │      FastAPI Server      │
                    │    (Lead Processing)     │
                    └─────────────┬─────────────┘
                                 │
                    ┌─────────────┴─────────────┐
                    │    Service Layer         │
                    │  ┌─────┐ ┌─────┐ ┌─────┐ │
                    │  │ LLM │ │Vec. │ │CRM  │ │
                    │  │Svc  │ │DB   │ │Sync │ │
                    │  └─────┘ └─────┘ └─────┘ │
                    └─────────────┬─────────────┘
                                 │
    ┌─────────────┐    ┌─────────┴───────┐    ┌─────────────┐
    │   Ollama    │    │   ChromaDB      │    │  Airtable   │
    │  (Local)    │    │  (Vectors)      │    │    API      │
    └─────────────┘    └─────────────────┘    └─────────────┘
```

### Service-Oriented Design
The system follows a service-oriented architecture with clear boundaries:

1. **API Layer**: FastAPI handles HTTP requests and responses
2. **Service Layer**: Business logic encapsulated in service classes
3. **Data Layer**: ChromaDB for vectors, Airtable for CRM data
4. **External Services**: Ollama for LLM inference

## Data Flow & Processing Pipeline

### Lead Intake Processing Flow
```
Input Message
     │
     ▼
┌─────────────────┐
│  Input Validation │ ← Pydantic models enforce schema
│  & Sanitization   │
└─────────┬───────┘
          │
          ▼
┌─────────────────┐
│   Store Raw     │ ← Persist original data immediately
│   Lead Data     │
└─────────┬───────┘
          │
          ▼
┌─────────────────┐
│  Generate       │ ← Create embeddings for similarity
│  Embeddings     │   search (async operation)
└─────────┬───────┘
          │
          ▼
┌─────────────────┐
│  Similarity     │ ← Check for duplicates before
│  Search         │   expensive LLM processing
└─────────┬───────┘
          │
          ▼
┌─────────────────┐
│  LLM Analysis   │ ← Extract entities, classify intent,
│  (Ollama)       │   score quality and urgency
└─────────┬───────┘
          │
          ▼
┌─────────────────┐
│  Enrich Lead    │ ← Combine original + AI analysis
│  Record         │
└─────────┬───────┘
          │
          ▼
┌─────────────────┐
│  Sync to        │ ← Push enriched data to CRM
│  Airtable       │   (with retry logic)
└─────────┬───────┘
          │
          ▼
┌─────────────────┐
│  Return Result  │ ← Response with enriched lead
│  to Client      │
└─────────────────┘
```

## Core Design Patterns

### Repository Pattern
Each external service has a dedicated service class acting as a repository:

```python
# Abstract base for consistency
class BaseService(ABC):
    @abstractmethod
    async def health_check(self) -> bool:
        pass

# Service implementations
class LLMService(BaseService):
    async def analyze_lead(self, message: str) -> LeadAnalysis:
        # Ollama integration logic
        
class VectorService(BaseService):
    async def find_similar_leads(self, embedding: List[float]) -> List[SimilarLead]:
        # ChromaDB similarity search
        
class CRMService(BaseService):
    async def sync_lead(self, lead: EnrichedLead) -> str:
        # Airtable synchronization
```

### Factory Pattern for Service Configuration
```python
class ServiceFactory:
    @staticmethod
    def create_llm_service(settings: Settings) -> LLMService:
        return LLMService(
            base_url=settings.ollama_base_url,
            model=settings.ollama_model,
            timeout=settings.ollama_timeout
        )
```

### Strategy Pattern for Business Types
Different business types require different analysis strategies:

```python
class LeadAnalysisStrategy(ABC):
    @abstractmethod
    def create_prompts(self) -> PromptTemplates:
        pass

class AutomotiveStrategy(LeadAnalysisStrategy):
    def create_prompts(self) -> PromptTemplates:
        return PromptTemplates(
            intent_classification="Classify automotive service request...",
            entity_extraction="Extract vehicle, service type, urgency..."
        )

class MedSpaStrategy(LeadAnalysisStrategy):
    def create_prompts(self) -> PromptTemplates:
        return PromptTemplates(
            intent_classification="Classify beauty/wellness inquiry...",
            entity_extraction="Extract treatment type, booking preference..."
        )
```

## Database Design Decisions

### ChromaDB Schema Design
```python
# Collection structure for semantic search
{
    "collection_name": "leads",
    "metadata": {
        "business_type": "automotive",
        "created_date": "2024-01-15",
        "lead_id": "lead_12345"
    },
    "documents": [
        "Customer message text content"
    ],
    "embeddings": [
        [0.1, 0.2, 0.3, ...]  # 384-dimensional vectors
    ],
    "ids": ["lead_12345"]
}
```

**Design Rationale**:
- **Single Collection**: Simpler management, cross-business similarity
- **Rich Metadata**: Enable filtering by business type, date ranges
- **Document Storage**: Keep original text for debugging and reprocessing
- **Embedding Strategy**: Use `all-MiniLM-L6-v2` for balance of speed/quality

### Airtable Schema Mapping
```python
# Internal model to Airtable field mapping
AIRTABLE_FIELD_MAPPING = {
    "lead_id": "Lead ID",
    "contact_info.name": "Name",
    "contact_info.email": "Email",
    "contact_info.phone": "Phone",
    "enrichment.intent": "Intent",
    "enrichment.urgency_score": "Urgency Score",
    "enrichment.service_type": "Service Type",
    "original_message": "Original Message",
    "created_at": "Created",
    "source": "Source"
}
```

**Design Rationale**:
- **Flexible Mapping**: Configurable field mappings per business
- **Nested Field Support**: Handle complex object structures
- **Type Conversion**: Automatic conversion between Python and Airtable types

## API Design Principles

### RESTful Resource Design
```python
# Resource-oriented endpoints
GET    /api/v1/leads              # List leads with pagination
POST   /api/v1/leads              # Create new lead (intake)
GET    /api/v1/leads/{id}         # Get specific lead
PUT    /api/v1/leads/{id}         # Update lead
DELETE /api/v1/leads/{id}         # Delete lead
GET    /api/v1/leads/{id}/similar # Find similar leads
POST   /api/v1/leads/batch        # Batch operations
```

### Request/Response Consistency
```python
# Standard response envelope
{
    "success": true,
    "data": { ... },
    "errors": [],
    "metadata": {
        "timestamp": "2024-01-15T10:30:00Z",
        "version": "1.0.0",
        "request_id": "req_12345"
    }
}

# Error response format
{
    "success": false,
    "data": null,
    "errors": [
        {
            "code": "VALIDATION_ERROR",
            "message": "Invalid email format",
            "field": "contact_info.email"
        }
    ],
    "metadata": { ... }
}
```

### Pagination Strategy
```python
# Cursor-based pagination for large datasets
{
    "data": [...],
    "pagination": {
        "has_more": true,
        "cursor": "eyJjcmVhdGVkX2F0IjoiMjAyNC0wMS0xNSJ9",
        "limit": 50,
        "total_estimate": 10000
    }
}
```

## Asynchronous Processing Design

### Background Task Architecture
```python
# FastAPI background tasks for non-blocking operations
@router.post("/intake")
async def create_lead(
    lead_input: LeadInput,
    background_tasks: BackgroundTasks
):
    # Immediate response with basic validation
    lead_id = await create_lead_record(lead_input)
    
    # Background processing
    background_tasks.add_task(
        process_lead_async,
        lead_id,
        lead_input
    )
    
    return {"lead_id": lead_id, "status": "processing"}

async def process_lead_async(lead_id: str, lead_input: LeadInput):
    # LLM analysis, vector search, CRM sync
    # Update lead record with results
```

### Retry and Circuit Breaker Pattern
```python
class CircuitBreaker:
    def __init__(self, failure_threshold: int = 5, timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN

    async def call(self, func, *args, **kwargs):
        if self.state == "OPEN":
            if time.time() - self.last_failure_time > self.timeout:
                self.state = "HALF_OPEN"
            else:
                raise CircuitBreakerOpenException()
        
        try:
            result = await func(*args, **kwargs)
            self.reset()
            return result
        except Exception as e:
            self.record_failure()
            raise e
```

## Error Handling Strategy

### Hierarchical Exception Design
```python
class BaseCampException(Exception):
    """Base exception for all application errors"""
    def __init__(self, message: str, code: str = None):
        self.message = message
        self.code = code or self.__class__.__name__
        super().__init__(message)

class ValidationError(BaseCampException):
    """Input validation failures"""
    pass

class ExternalServiceError(BaseCampException):
    """External service integration failures"""
    pass

class LLMServiceError(ExternalServiceError):
    """Ollama/LLM specific errors"""
    pass

class VectorServiceError(ExternalServiceError):
    """ChromaDB specific errors"""
    pass

class CRMServiceError(ExternalServiceError):
    """Airtable/CRM specific errors"""
    pass
```

### Graceful Degradation
```python
async def process_lead_with_fallback(lead_input: LeadInput) -> EnrichedLead:
    lead = EnrichedLead.from_input(lead_input)
    
    try:
        # Try full AI analysis
        analysis = await llm_service.analyze_lead(lead_input.message)
        lead.enrichment = analysis
    except LLMServiceError:
        logger.warning("LLM service unavailable, using basic analysis")
        lead.enrichment = create_basic_analysis(lead_input)
    
    try:
        # Try similarity search
        similar = await vector_service.find_similar_leads(lead)
        lead.similar_leads = similar
    except VectorServiceError:
        logger.warning("Vector service unavailable, skipping similarity")
        lead.similar_leads = []
    
    return lead
```

## Performance Optimization Strategies

### Caching Architecture
```python
# Multi-level caching strategy
class CacheService:
    def __init__(self):
        self.memory_cache = {}  # LRU cache for frequent queries
        self.redis_cache = None  # Distributed cache (future)
    
    async def get_or_compute(
        self, 
        key: str, 
        compute_func: Callable,
        ttl: int = 3600
    ):
        # L1: Memory cache
        if key in self.memory_cache:
            return self.memory_cache[key]
        
        # L2: Redis cache (future)
        # if self.redis_cache:
        #     result = await self.redis_cache.get(key)
        #     if result:
        #         return result
        
        # Compute and cache
        result = await compute_func()
        self.memory_cache[key] = result
        return result
```

### Batch Processing Optimization
```python
# Batch embeddings for efficiency
async def process_leads_batch(leads: List[LeadInput]) -> List[EnrichedLead]:
    # Generate embeddings in batch
    messages = [lead.message for lead in leads]
    embeddings = await vector_service.generate_embeddings_batch(messages)
    
    # Process LLM analysis in parallel
    tasks = [
        llm_service.analyze_lead(lead.message)
        for lead in leads
    ]
    analyses = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Combine results
    return [
        create_enriched_lead(lead, embedding, analysis)
        for lead, embedding, analysis in zip(leads, embeddings, analyses)
    ]
```

### Database Query Optimization
```python
# Optimized similarity search with metadata filtering
async def find_similar_leads_optimized(
    embedding: List[float],
    business_type: str = None,
    max_results: int = 10,
    similarity_threshold: float = 0.85
) -> List[SimilarLead]:
    
    # Build metadata filter
    where_clause = {}
    if business_type:
        where_clause["business_type"] = business_type
    
    # Perform optimized query
    results = collection.query(
        query_embeddings=[embedding],
        n_results=max_results,
        where=where_clause,
        include=["distances", "metadatas", "documents"]
    )
    
    # Filter by similarity threshold
    return [
        SimilarLead(
            id=results["ids"][0][i],
            similarity=1 - results["distances"][0][i],
            metadata=results["metadatas"][0][i]
        )
        for i in range(len(results["ids"][0]))
        if (1 - results["distances"][0][i]) >= similarity_threshold
    ]
```

## Security Design Considerations

### Input Validation & Sanitization
```python
class SecureLeadInput(BaseModel):
    message: str = Field(
        ...,
        min_length=1,
        max_length=10000,
        description="Lead message content"
    )
    
    @validator('message')
    def sanitize_message(cls, v):
        # Remove potentially harmful content
        v = html.escape(v)  # Escape HTML
        v = re.sub(r'<script.*?</script>', '', v, flags=re.IGNORECASE)
        return v.strip()
    
    @validator('contact_info')
    def validate_contact_info(cls, v):
        # PII validation and masking
        if v.email:
            if not re.match(r'^[^@]+@[^@]+\.[^@]+$', v.email):
                raise ValueError('Invalid email format')
        return v
```

### Rate Limiting Implementation
```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.post("/api/v1/intake")
@limiter.limit("10/minute")  # 10 requests per minute per IP
async def create_lead(request: Request, lead_input: LeadInput):
    # Process lead
    pass
```

### Data Privacy & Compliance
```python
class PIIHandler:
    @staticmethod
    def mask_sensitive_data(lead: EnrichedLead) -> EnrichedLead:
        # Mask PII in logs and external services
        masked_lead = lead.copy()
        if masked_lead.contact_info.email:
            masked_lead.contact_info.email = mask_email(lead.contact_info.email)
        if masked_lead.contact_info.phone:
            masked_lead.contact_info.phone = mask_phone(lead.contact_info.phone)
        return masked_lead
    
    @staticmethod
    def audit_log_access(user_id: str, lead_id: str, action: str):
        # Log all access to sensitive data
        logger.info(
            "Data access audit",
            extra={
                "user_id": user_id,
                "lead_id": lead_id,
                "action": action,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
```

## Testing Strategy Design

### Test Pyramid Implementation
```python
# Unit Tests (70%)
class TestLLMService:
    @pytest.fixture
    def mock_ollama_client(self):
        return Mock()
    
    async def test_analyze_lead_success(self, mock_ollama_client):
        # Test individual service methods
        pass

# Integration Tests (20%)
class TestLeadProcessingIntegration:
    @pytest.fixture
    async def test_app(self):
        # Real FastAPI app with test database
        pass
    
    async def test_end_to_end_lead_processing(self, test_app):
        # Test complete workflow
        pass

# E2E Tests (10%)
class TestFullSystemE2E:
    async def test_real_world_lead_scenario(self):
        # Test against real external services in staging
        pass
```

### Mock Strategy for External Services
```python
# Ollama mock responses
MOCK_LLM_RESPONSES = {
    "automotive_service": {
        "intent": "service_request",
        "entities": {"service_type": "brake_repair", "urgency": "medium"},
        "urgency_score": 0.7
    }
}

class MockOllamaService:
    async def analyze_lead(self, message: str) -> LeadAnalysis:
        # Return deterministic responses for testing
        if "brake" in message.lower():
            return LeadAnalysis(**MOCK_LLM_RESPONSES["automotive_service"])
```

## Monitoring and Observability

### Structured Logging Design
```python
import structlog

logger = structlog.get_logger()

# Context-aware logging
async def process_lead(lead_input: LeadInput):
    log = logger.bind(
        lead_id=lead_input.id,
        source=lead_input.source,
        business_type=lead_input.business_type
    )
    
    log.info("Starting lead processing")
    
    try:
        result = await enrich_lead(lead_input)
        log.info("Lead processing completed", 
                processing_time=result.processing_time,
                enrichment_score=result.enrichment.quality_score)
    except Exception as e:
        log.error("Lead processing failed", error=str(e))
        raise
```

### Metrics Collection
```python
from prometheus_client import Counter, Histogram, Gauge

# Application metrics
LEADS_PROCESSED = Counter('leads_processed_total', 'Total leads processed')
PROCESSING_TIME = Histogram('lead_processing_seconds', 'Lead processing time')
ACTIVE_CONNECTIONS = Gauge('active_connections', 'Active API connections')
LLM_RESPONSE_TIME = Histogram('llm_response_seconds', 'LLM response time')
```

This design provides a solid foundation for building a scalable, maintainable AI-powered lead processing system while maintaining flexibility for future enhancements.