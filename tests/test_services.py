"""Tests for service layer with mocked dependencies."""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import httpx
from src.models.lead import (
    AIAnalysis,
    EnrichedLead,
    IntentCategory,
    LeadInput,
    UrgencyLevel,
    VectorData
)
from src.models.airtable import SyncRecord, SyncStatus
from src.services.llm_service import (
    LLMServiceError,
    LLMTimeoutError,
    OllamaService
)
from src.services.vector_service import (
    ChromaVectorService,
    SimilarityResult,
    VectorServiceError
)
from src.services.airtable_service import (
    AirtableService,
    AirtableConfig,
    CRMServiceError
)


@pytest.mark.service
class TestLLMService:
    """Test LLM service functionality."""
    
    @pytest.fixture
    def ollama_service(self):
        """Create OllamaService instance for testing."""
        return OllamaService()
    
    @pytest.fixture
    def mock_ollama_response(self):
        """Mock successful Ollama API response."""
        return {
            "message": {
                "content": json.dumps({
                    "intent": "appointment_request",
                    "intent_confidence": 0.85,
                    "urgency": "high",
                    "urgency_confidence": 0.78,
                    "entities": {
                        "services": ["brake repair"],
                        "symptoms": ["grinding noise"]
                    },
                    "quality_score": 82,
                    "topics": ["brake_repair", "automotive"],
                    "summary": "Customer needs brake repair appointment",
                    "business_insights": {
                        "service_category": "repair",
                        "customer_type": "new"
                    }
                })
            },
            "model": "mistral:latest",
            "total_duration": 1500000000,
            "eval_count": 150
        }
    
    async def test_analyze_lead_success(
        self, 
        ollama_service, 
        sample_lead_input, 
        mock_ollama_response
    ):
        """Test successful lead analysis."""
        with patch.object(ollama_service, '_make_ollama_request') as mock_request:
            mock_request.return_value = MagicMock(
                content=mock_ollama_response["message"]["content"],
                model=mock_ollama_response["model"]
            )
            
            analysis = await ollama_service.analyze_lead(sample_lead_input)
            
            assert isinstance(analysis, AIAnalysis)
            assert analysis.intent == IntentCategory.APPOINTMENT_REQUEST
            assert analysis.intent_confidence == 0.85
            assert analysis.urgency == UrgencyLevel.HIGH
            assert analysis.quality_score == 82
            assert analysis.model_used == "mistral:latest"
            assert analysis.processing_time > 0
            
            mock_request.assert_called_once()
    
    async def test_analyze_lead_invalid_json(
        self, 
        ollama_service, 
        sample_lead_input
    ):
        """Test handling of invalid JSON response."""
        with patch.object(ollama_service, '_make_ollama_request') as mock_request:
            mock_request.return_value = MagicMock(
                content="invalid json response",
                model="mistral:latest"
            )
            
            # Should fall back to basic analysis
            analysis = await ollama_service.analyze_lead(sample_lead_input)
            
            assert isinstance(analysis, AIAnalysis)
            assert analysis.model_used == "mistral:latest_fallback"
            assert "fallback_analysis" in analysis.topics
    
    async def test_analyze_lead_http_error(
        self, 
        ollama_service, 
        sample_lead_input
    ):
        """Test handling of HTTP errors."""
        with patch.object(ollama_service, '_make_ollama_request') as mock_request:
            mock_request.side_effect = httpx.HTTPStatusError(
                "Server error", 
                request=MagicMock(),
                response=MagicMock(status_code=500)
            )
            
            # Should return fallback analysis
            analysis = await ollama_service.analyze_lead(sample_lead_input)
            
            assert isinstance(analysis, AIAnalysis)
            assert "fallback" in analysis.model_used
    
    async def test_health_check(self, ollama_service):
        """Test health check functionality."""
        with patch.object(ollama_service.client, 'get') as mock_get:
            mock_get.return_value = MagicMock(status_code=200)
            
            result = await ollama_service.health_check()
            assert result is True
            
            mock_get.assert_called_once_with(f"{ollama_service.base_url}/api/tags")
    
    async def test_get_available_models(self, ollama_service):
        """Test getting available models."""
        mock_response = {
            "models": [
                {"name": "mistral:latest"},
                {"name": "llama2:7b"}
            ]
        }
        
        with patch.object(ollama_service.client, 'get') as mock_get:
            mock_get.return_value = MagicMock(
                status_code=200,
                json=lambda: mock_response
            )
            
            models = await ollama_service.get_available_models()
            assert models == ["mistral:latest", "llama2:7b"]
    
    def test_prompt_template_selection(self, ollama_service):
        """Test business-specific prompt template selection."""
        # Test that all business types have templates
        assert "general" in ollama_service.prompt_templates
        assert "automotive" in ollama_service.prompt_templates
        assert "medspa" in ollama_service.prompt_templates
        assert "consulting" in ollama_service.prompt_templates
        
        # Test template formatting
        template = ollama_service.prompt_templates["automotive"]
        system, user = template.format(
            message="Car brake issue",
            contact_info="John Doe",
            source="web_form"
        )
        
        assert "automotive" in system.lower()
        assert "Car brake issue" in user
        assert "John Doe" in user


@pytest.mark.service
class TestVectorService:
    """Test vector service functionality."""
    
    @pytest.fixture
    def vector_service(self):
        """Create ChromaVectorService instance for testing."""
        with patch('src.services.vector_service.chromadb.PersistentClient'):
            with patch('src.services.vector_service.SentenceTransformer'):
                service = ChromaVectorService()
                service.collection = MagicMock()
                service.embedding_model = MagicMock()
                return service
    
    async def test_add_lead(self, vector_service, sample_enriched_lead):
        """Test adding lead to vector database."""
        # Mock embedding generation
        mock_embedding = [0.1, 0.2, 0.3] * 128
        vector_service.embedding_model.encode.return_value = mock_embedding
        
        # Mock collection add
        vector_service.collection.add = MagicMock()
        
        vector_data = await vector_service.add_lead(sample_enriched_lead)
        
        assert isinstance(vector_data, VectorData)
        assert vector_data.embedding == mock_embedding
        assert vector_data.embedding_model == vector_service.embedding_model_name
        assert len(vector_data.text_hash) > 0
        
        # Verify collection.add was called
        vector_service.collection.add.assert_called_once()
    
    async def test_find_similar_leads(
        self, 
        vector_service, 
        sample_lead_input,
        sample_similarity_results
    ):
        """Test finding similar leads."""
        # Mock embedding generation
        mock_embedding = [0.1, 0.2, 0.3] * 128
        vector_service.embedding_model.encode.return_value = mock_embedding
        
        # Mock collection query response
        mock_query_result = {
            "ids": [[str(result.lead_id) for result in sample_similarity_results]],
            "distances": [[1.0 - result.similarity_score for result in sample_similarity_results]],
            "metadatas": [[result.metadata for result in sample_similarity_results]]
        }
        vector_service.collection.query.return_value = mock_query_result
        
        results = await vector_service.find_similar_leads(
            sample_lead_input, 
            threshold=0.8, 
            limit=5
        )
        
        assert len(results) == 2  # Both results are above 0.8 threshold
        assert all(isinstance(result, SimilarityResult) for result in results)
        assert results[0].similarity_score > results[1].similarity_score  # Sorted
        
        vector_service.collection.query.assert_called_once()
    
    async def test_remove_lead(self, vector_service):
        """Test removing lead from vector database."""
        lead_id = uuid4()
        
        # Mock existing lead
        vector_service.collection.get.return_value = {"ids": [str(lead_id)]}
        vector_service.collection.delete = MagicMock()
        
        result = await vector_service.remove_lead(lead_id)
        
        assert result is True
        vector_service.collection.delete.assert_called_once_with(ids=[str(lead_id)])
    
    async def test_remove_nonexistent_lead(self, vector_service):
        """Test removing non-existent lead."""
        lead_id = uuid4()
        
        # Mock non-existent lead
        vector_service.collection.get.return_value = {"ids": []}
        
        result = await vector_service.remove_lead(lead_id)
        
        assert result is False
    
    async def test_health_check(self, vector_service):
        """Test vector service health check."""
        # Mock successful health check components
        vector_service.client = MagicMock()
        vector_service.collection = MagicMock()
        vector_service.embedding_model = MagicMock()
        vector_service.embedding_model.encode.return_value = [0.1, 0.2, 0.3]
        vector_service.collection.query.return_value = {"ids": []}
        
        result = await vector_service.health_check()
        assert result is True
    
    def test_text_preparation(self, vector_service, sample_lead_input):
        """Test lead text preparation for embedding."""
        text = vector_service._prepare_lead_text(sample_lead_input)
        
        assert sample_lead_input.message in text
        assert sample_lead_input.contact.full_name in text
        assert sample_lead_input.contact.company in text
        
        # Test custom fields inclusion
        for key, value in sample_lead_input.custom_fields.items():
            assert f"{key}: {value}" in text


@pytest.mark.service
class TestAirtableService:
    """Test Airtable service functionality."""
    
    @pytest.fixture
    def airtable_config(self):
        """Create test Airtable configuration."""
        return AirtableConfig(
            base_id="appTEST123456789",
            table_name="TestLeads",
            api_key="patTEST123456789"
        )
    
    @pytest.fixture
    def airtable_service(self, airtable_config):
        """Create AirtableService instance for testing."""
        with patch('src.services.airtable_service.Api'):
            service = AirtableService(airtable_config)
            service.table = MagicMock()
            return service
    
    async def test_sync_lead_create(self, airtable_service, sample_enriched_lead):
        """Test creating new lead in Airtable."""
        # Mock successful create
        mock_created_record = {"id": "recTEST123", "fields": {}}
        airtable_service.table.create.return_value = mock_created_record
        
        sync_result = await airtable_service.sync_lead(sample_enriched_lead)
        
        assert isinstance(sync_result, SyncRecord)
        assert sync_result.status == SyncStatus.SUCCESS
        assert sync_result.airtable_record_id == "recTEST123"
        assert sync_result.operation.value == "create"
        
        airtable_service.table.create.assert_called_once()
    
    async def test_sync_lead_update(self, airtable_service, sample_enriched_lead):
        """Test updating existing lead in Airtable."""
        # Set existing external ID
        sample_enriched_lead.external_ids["airtable"] = "recEXISTING123"
        
        # Mock successful update
        mock_updated_record = {"id": "recEXISTING123", "fields": {}}
        airtable_service.table.update.return_value = mock_updated_record
        
        sync_result = await airtable_service.sync_lead(sample_enriched_lead)
        
        assert sync_result.status == SyncStatus.SUCCESS
        assert sync_result.operation.value == "update"
        
        airtable_service.table.update.assert_called_once()
    
    async def test_sync_lead_failure(self, airtable_service, sample_enriched_lead):
        """Test handling Airtable API failures."""
        from pyairtable.exceptions import AirtableApiError
        
        # Mock API error
        airtable_service.table.create.side_effect = AirtableApiError(
            "API Error",
            response=MagicMock(status_code=400)
        )
        
        sync_result = await airtable_service.sync_lead(sample_enriched_lead)
        
        assert sync_result.status == SyncStatus.FAILED
        assert sync_result.error_message is not None
    
    async def test_batch_sync(self, airtable_service, sample_enriched_lead):
        """Test batch synchronization."""
        leads = [sample_enriched_lead]
        
        # Mock successful batch create
        mock_created_records = [{"id": "recBATCH123", "fields": {}}]
        airtable_service.table.batch_create.return_value = mock_created_records
        
        batch_result = await airtable_service.sync_leads_batch(leads)
        
        assert batch_result.total_operations == 1
        assert batch_result.successful_operations == 1
        assert batch_result.success_rate == 100.0
        assert batch_result.is_complete is True
    
    async def test_health_check(self, airtable_service):
        """Test Airtable service health check."""
        # Mock successful schema response
        mock_schema = {
            "fields": [
                {"name": "First Name", "type": "singleLineText"},
                {"name": "Email", "type": "email"}
            ]
        }
        airtable_service.table.schema.return_value = mock_schema
        
        result = await airtable_service.health_check()
        assert result is True
        
        airtable_service.table.schema.assert_called_once()
    
    def test_field_mapping_validation(self, airtable_service):
        """Test field mapping validation against schema."""
        mock_schema = {
            "fields": [
                {"name": "First Name"},
                {"name": "Last Name"},
                {"name": "Email"},
                {"name": "Message"}
            ]
        }
        airtable_service.table.schema.return_value = mock_schema
        
        validation_results = airtable_service.get_field_mapping_validation()
        
        assert validation_results["first_name_field"] is True
        assert validation_results["last_name_field"] is True
        assert validation_results["email_field"] is True
        assert validation_results["message_field"] is True


@pytest.mark.service
class TestServiceFactories:
    """Test service factory functions."""
    
    def test_llm_service_factory(self):
        """Test LLM service factory function."""
        from src.services.llm_service import create_llm_service, get_llm_service
        
        service = create_llm_service()
        assert service is not None
        
        # Test singleton behavior would require resetting global state
        # which is complex in tests, so we just verify the function works
    
    def test_vector_service_factory(self):
        """Test vector service factory function."""
        from src.services.vector_service import create_vector_service
        
        with patch('src.services.vector_service.chromadb.PersistentClient'):
            with patch('src.services.vector_service.SentenceTransformer'):
                service = create_vector_service()
                assert service is not None
    
    def test_crm_service_factory(self):
        """Test CRM service factory function."""
        from src.services.airtable_service import create_crm_service
        
        with patch('src.services.airtable_service.Api'):
            service = create_crm_service()
            assert service is not None


@pytest.mark.service
class TestServiceErrorHandling:
    """Test service error handling and resilience."""
    
    async def test_llm_service_timeout(self):
        """Test LLM service timeout handling."""
        service = OllamaService()
        
        with patch.object(service.client, 'post') as mock_post:
            mock_post.side_effect = httpx.TimeoutException("Request timeout")
            
            # Should raise LLMTimeoutError
            with pytest.raises(LLMTimeoutError):
                await service._make_ollama_request("system", "user")
    
    async def test_vector_service_embedding_error(self):
        """Test vector service embedding generation errors."""
        with patch('src.services.vector_service.chromadb.PersistentClient'):
            with patch('src.services.vector_service.SentenceTransformer'):
                service = ChromaVectorService()
                service.embedding_model = MagicMock()
                service.embedding_model.encode.side_effect = Exception("Model error")
                
                # Should raise EmbeddingError
                with pytest.raises(Exception):
                    service._generate_embedding("test text")
    
    async def test_crm_service_rate_limiting(self, airtable_service, sample_enriched_lead):
        """Test CRM service rate limiting behavior."""
        from pyairtable.exceptions import AirtableApiError
        
        # Mock rate limit error
        airtable_service.table.create.side_effect = AirtableApiError(
            "RATE_LIMITED",
            response=MagicMock(status_code=429)
        )
        
        sync_result = await airtable_service.sync_lead(sample_enriched_lead)
        
        assert sync_result.status == SyncStatus.FAILED
        assert "Rate limit" in sync_result.error_message


if __name__ == "__main__":
    pytest.main([__file__])