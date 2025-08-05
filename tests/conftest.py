"""Pytest configuration and fixtures for baseCamp tests."""

import asyncio
import os
from typing import AsyncGenerator, Dict, Generator
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient

# Set test environment variables
os.environ["DEBUG"] = "true"
os.environ["ENABLE_API_DOCS"] = "true"
os.environ["OLLAMA_BASE_URL"] = "http://localhost:11434"
os.environ["OLLAMA_MODEL"] = "mistral:latest"
os.environ["CHROMA_PERSIST_DIRECTORY"] = "./test_chroma_db"
# Disable Airtable integration for tests (no API key provided)
os.environ["AIRTABLE_API_KEY"] = ""
os.environ["AIRTABLE_BASE_ID"] = ""
os.environ["AIRTABLE_TABLE_NAME"] = "TestLeads"

from src.main import app
from src.models.lead import (
    AIAnalysis,
    ContactInfo,
    EnrichedLead,
    IntentCategory,
    LeadInput,
    LeadSource,
    UrgencyLevel,
    VectorData
)
from src.models.airtable import AirtableRecord, SyncRecord, SyncStatus
from src.services.llm_service import LLMServiceInterface
from src.services.vector_service import VectorServiceInterface, SimilarityResult
from src.services.airtable_service import CRMServiceInterface


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def client(mock_services) -> Generator[TestClient, None, None]:
    """Create a test client for the FastAPI application."""
    # Import services here to avoid circular imports
    from src.services.llm_service import get_llm_service
    from src.services.vector_service import get_vector_service
    from src.services.airtable_service import get_crm_service
    
    # Override dependencies with mock services
    app.dependency_overrides[get_llm_service] = lambda: mock_services["llm"]
    app.dependency_overrides[get_vector_service] = lambda: mock_services["vector"]
    app.dependency_overrides[get_crm_service] = lambda: mock_services["crm"]
    
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        # Clean up dependency overrides
        app.dependency_overrides.clear()


@pytest.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Create an async test client for the FastAPI application."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


# Test data fixtures
@pytest.fixture
def sample_contact_info() -> ContactInfo:
    """Sample contact information for testing."""
    return ContactInfo(
        first_name="John",
        last_name="Doe",
        email="john.doe@example.com",
        phone="+1234567890",
        company="Test Company"
    )


@pytest.fixture
def sample_lead_input(sample_contact_info: ContactInfo) -> LeadInput:
    """Sample lead input for testing."""
    return LeadInput(
        message="My car is making strange noises when I brake",
        contact=sample_contact_info,
        source=LeadSource.WEB_FORM,
        source_url="https://example.com/contact",
        custom_fields={"vehicle_type": "sedan", "preferred_time": "morning"}
    )


@pytest.fixture
def sample_ai_analysis() -> AIAnalysis:
    """Sample AI analysis for testing."""
    return AIAnalysis(
        intent=IntentCategory.APPOINTMENT_REQUEST,
        intent_confidence=0.85,
        urgency=UrgencyLevel.HIGH,
        urgency_confidence=0.78,
        entities={
            "services": ["brake repair"],
            "symptoms": ["grinding noise", "vibration"],
            "vehicle_info": ["sedan"]
        },
        quality_score=82,
        topics=["brake_repair", "automotive_service"],
        summary="Customer experiencing brake issues, needs appointment for repair",
        business_insights={
            "service_category": "repair",
            "customer_type": "new",
            "vehicle_age": "used"
        },
        model_used="mistral:latest",
        processing_time=1.25
    )


@pytest.fixture
def sample_vector_data() -> VectorData:
    """Sample vector data for testing."""
    return VectorData(
        embedding=[0.1, 0.2, 0.3, 0.4, 0.5] * 77,  # 385 dimensions
        embedding_model="all-MiniLM-L6-v2",
        text_hash="abc123def456"
    )


@pytest.fixture
def sample_enriched_lead(
    sample_lead_input: LeadInput,
    sample_ai_analysis: AIAnalysis,
    sample_vector_data: VectorData
) -> EnrichedLead:
    """Sample enriched lead for testing."""
    lead = EnrichedLead(**sample_lead_input.dict())
    lead.mark_enriched(sample_ai_analysis)
    lead.vector_data = sample_vector_data
    return lead


@pytest.fixture
def sample_similarity_results() -> list[SimilarityResult]:
    """Sample similarity search results."""
    return [
        SimilarityResult(
            lead_id=uuid4(),
            similarity_score=0.92,
            metadata={
                "message": "Car brakes are squealing",
                "source": "web_form",
                "quality_score": 75,
                "intent": "appointment_request"
            }
        ),
        SimilarityResult(
            lead_id=uuid4(),
            similarity_score=0.87,
            metadata={
                "message": "Need brake inspection",
                "source": "phone",
                "quality_score": 68,
                "intent": "inquiry"
            }
        )
    ]


# Mock service fixtures
@pytest.fixture
def mock_llm_service(sample_ai_analysis: AIAnalysis) -> AsyncMock:
    """Mock LLM service for testing."""
    mock_service = AsyncMock(spec=LLMServiceInterface)
    mock_service.analyze_lead.return_value = sample_ai_analysis
    mock_service.health_check.return_value = True
    mock_service.get_available_models.return_value = ["mistral:latest", "llama2:7b"]
    return mock_service


@pytest.fixture
def mock_vector_service(
    sample_vector_data: VectorData,
    sample_similarity_results: list[SimilarityResult]
) -> AsyncMock:
    """Mock vector service for testing."""
    mock_service = AsyncMock(spec=VectorServiceInterface)
    mock_service.add_lead.return_value = sample_vector_data
    mock_service.find_similar_leads.return_value = sample_similarity_results
    mock_service.update_lead.return_value = sample_vector_data
    mock_service.remove_lead.return_value = True
    mock_service.health_check.return_value = True
    return mock_service


@pytest.fixture
def mock_crm_service() -> AsyncMock:
    """Mock CRM service for testing."""
    mock_service = AsyncMock(spec=CRMServiceInterface)
    
    # Create mock sync record
    sync_record = SyncRecord(
        lead_id=uuid4(),
        operation="create",
        base_id="test_base_id",
        table_name="TestLeads"
    )
    sync_record.mark_success("rec123456")
    
    mock_service.sync_lead.return_value = sync_record
    mock_service.update_lead.return_value = sync_record
    mock_service.delete_lead.return_value = True
    mock_service.health_check.return_value = True
    
    return mock_service


@pytest.fixture
def mock_services(
    mock_llm_service: AsyncMock,
    mock_vector_service: AsyncMock,
    mock_crm_service: AsyncMock
) -> Dict[str, AsyncMock]:
    """Collection of all mock services."""
    return {
        "llm": mock_llm_service,
        "vector": mock_vector_service,
        "crm": mock_crm_service
    }


# Test data generators
@pytest.fixture
def lead_input_factory():
    """Factory for creating test lead inputs."""
    def _create_lead_input(
        message: str = "Test message",
        first_name: str = "Test",
        last_name: str = "User",
        email: str = "test@example.com",
        phone: str = "+1234567890",
        source: LeadSource = LeadSource.WEB_FORM,
        **kwargs
    ) -> LeadInput:
        contact = ContactInfo(
            first_name=first_name,
            last_name=last_name,
            email=email,
            phone=phone
        )
        return LeadInput(
            message=message,
            contact=contact,
            source=source,
            **kwargs
        )
    return _create_lead_input


# Utility fixtures
@pytest.fixture
def clean_test_db():
    """Clean up test database files after tests."""
    yield
    # Cleanup test ChromaDB directory if it exists
    import shutil
    test_db_path = "./test_chroma_db"
    if os.path.exists(test_db_path):
        shutil.rmtree(test_db_path, ignore_errors=True)