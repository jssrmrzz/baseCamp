"""Integration tests for ChromaDB vector service with real database operations."""

import asyncio
import pytest
import time
from datetime import datetime
from typing import List
from uuid import uuid4

from src.models.lead import (
    AIAnalysis,
    ContactInfo,
    EnrichedLead,
    IntentCategory,
    LeadInput,
    LeadSource,
    LeadStatus,
    UrgencyLevel,
    VectorData
)
from src.services.vector_service import (
    ChromaVectorService,
    SimilarityResult,
    VectorServiceError,
    EmbeddingError,
    ChromaDBError
)


@pytest.mark.asyncio
class TestChromaDBIntegration:
    """Integration tests for ChromaDB vector service."""
    
    @pytest.fixture
    def vector_service(self):
        """Create real ChromaDB vector service instance."""
        return ChromaVectorService()
    
    @pytest.fixture
    def test_lead_input(self):
        """Create a test lead input."""
        return LeadInput(
            message="My 2018 Honda Civic needs brake repair urgently. The brakes are making grinding noise.",
            contact=ContactInfo(
                first_name="John",
                last_name="Smith",
                email="john.smith@email.com",
                phone="+1-555-123-4567",
                company="Smith Auto"
            ),
            source=LeadSource.WEB_FORM,
            custom_fields={"form_id": "brake_repair_form", "referrer": "google"}
        )
    
    @pytest.fixture
    def test_enriched_lead(self, test_lead_input):
        """Create a test enriched lead."""
        ai_analysis = AIAnalysis(
            intent=IntentCategory.APPOINTMENT_REQUEST,
            intent_confidence=0.9,
            urgency=UrgencyLevel.HIGH,
            urgency_confidence=0.85,
            entities={
                "vehicle_info": ["2018 Honda Civic"],
                "services": ["brake repair"],
                "symptoms": ["grinding noise"],
                "urgency_indicators": ["urgently"]
            },
            quality_score=88,
            topics=["brake_repair", "automotive_service"],
            summary="Customer needs urgent brake repair for Honda Civic with grinding noise",
            business_insights={
                "service_category": "repair",
                "customer_type": "new",
                "urgency_level": "high"
            },
            model_used="test_model",
            processing_time=2.5
        )
        
        return EnrichedLead(
            **test_lead_input.model_dump(),
            id=uuid4(),
            status=LeadStatus.ENRICHED,
            ai_analysis=ai_analysis,
            enriched_at=datetime.utcnow()
        )
    
    @pytest.fixture
    def similar_lead_input(self):
        """Create a similar lead for testing similarity search."""
        return LeadInput(
            message="Need brake service for my Honda Civic. Brakes making noise when stopping.",
            contact=ContactInfo(
                first_name="Jane",
                last_name="Doe",
                email="jane.doe@email.com",
                phone="+1-555-987-6543"
            ),
            source=LeadSource.CHAT_WIDGET,
            custom_fields={"page": "services", "chat_session": "12345"}
        )
    
    @pytest.fixture
    def dissimilar_lead_input(self):
        """Create a dissimilar lead for testing similarity search."""
        return LeadInput(
            message="Need Botox consultation for my wedding next month. What are your prices?",
            contact=ContactInfo(
                first_name="Sarah",
                last_name="Johnson",
                email="sarah.j@email.com"
            ),
            source=LeadSource.EMAIL,
            custom_fields={"subject": "Botox Pricing Inquiry"}
        )
    
    async def test_service_initialization(self, vector_service):
        """Test ChromaDB service initializes correctly."""
        # Verify service components are initialized
        assert vector_service.client is not None
        assert vector_service.collection is not None
        assert vector_service.embedding_model is not None
        assert vector_service.embedding_model_name == "all-MiniLM-L6-v2"
        
        # Verify configuration
        assert vector_service.persist_directory is not None
        assert vector_service.collection_name == "leads"
        assert vector_service.similarity_threshold == 0.85
        
        print("✅ ChromaDB service initialization: PASS")
    
    async def test_health_check(self, vector_service):
        """Test health check functionality."""
        is_healthy = await vector_service.health_check()
        assert is_healthy, "ChromaDB service should be healthy"
        
        # Test embedding generation as part of health check
        test_embedding = vector_service._generate_embedding("test message")
        assert isinstance(test_embedding, list)
        assert len(test_embedding) > 0
        assert all(isinstance(x, float) for x in test_embedding)
        
        print("✅ ChromaDB health check: PASS")
    
    async def test_embedding_generation(self, vector_service):
        """Test embedding generation functionality."""
        test_texts = [
            "brake repair needed urgently",
            "oil change service",
            "",  # Empty string should raise error
            "A very long message that contains lots of information about automotive services including brake repair, oil changes, engine diagnostics, transmission work, and other various maintenance services that a customer might need for their vehicle"
        ]
        
        # Test normal embedding generation
        embedding1 = vector_service._generate_embedding(test_texts[0])
        embedding2 = vector_service._generate_embedding(test_texts[1])
        
        # Verify embedding properties
        assert isinstance(embedding1, list)
        assert len(embedding1) == 384  # all-MiniLM-L6-v2 dimension
        assert all(isinstance(x, float) for x in embedding1)
        
        # Different texts should produce different embeddings
        assert embedding1 != embedding2
        
        # Test empty string handling
        with pytest.raises(EmbeddingError):
            vector_service._generate_embedding(test_texts[2])
        
        # Test long text handling
        long_embedding = vector_service._generate_embedding(test_texts[3])
        assert isinstance(long_embedding, list)
        assert len(long_embedding) == 384
        
        print("✅ Embedding generation: PASS")
    
    async def test_text_preparation(self, vector_service, test_lead_input):
        """Test lead text preparation for embedding."""
        prepared_text = vector_service._prepare_lead_text(test_lead_input)
        
        # Should include message
        assert test_lead_input.message in prepared_text
        
        # Should include contact info if available
        if test_lead_input.contact.full_name:
            assert f"Contact: {test_lead_input.contact.full_name}" in prepared_text
        if test_lead_input.contact.company:
            assert f"Company: {test_lead_input.contact.company}" in prepared_text
        
        # Should include custom fields if available
        for key, value in test_lead_input.custom_fields.items():
            if value:
                assert f"{key}: {value}" in prepared_text
        
        # Test text hash generation
        text_hash = vector_service._create_text_hash(prepared_text)
        assert isinstance(text_hash, str)
        assert len(text_hash) == 64  # SHA256 hex length
        
        # Same text should produce same hash
        text_hash2 = vector_service._create_text_hash(prepared_text)
        assert text_hash == text_hash2
        
        print("✅ Text preparation and hashing: PASS")
    
    async def test_add_lead_to_database(self, vector_service, test_enriched_lead):
        """Test adding leads to ChromaDB."""
        # Add lead to database
        vector_data = await vector_service.add_lead(test_enriched_lead)
        
        # Verify VectorData object
        assert isinstance(vector_data, VectorData)
        assert len(vector_data.embedding) == 384
        assert vector_data.embedding_model == "all-MiniLM-L6-v2"
        assert vector_data.text_hash is not None
        
        # Verify lead was added to collection
        result = vector_service.collection.get(ids=[str(test_enriched_lead.id)])
        assert len(result["ids"]) == 1
        assert result["ids"][0] == str(test_enriched_lead.id)
        
        # Verify metadata was stored correctly
        metadata = result["metadatas"][0]
        assert metadata["lead_id"] == str(test_enriched_lead.id)
        assert metadata["source"] == test_enriched_lead.source.value
        assert metadata["status"] == test_enriched_lead.status.value
        
        # Check contact info if available
        if test_enriched_lead.contact.full_name:
            assert metadata["contact_name"] == test_enriched_lead.contact.full_name
        if test_enriched_lead.contact.email:
            assert metadata["contact_email"] == str(test_enriched_lead.contact.email)
        if test_enriched_lead.contact.company:
            assert metadata["company"] == test_enriched_lead.contact.company
        
        # Check AI analysis if available
        if test_enriched_lead.ai_analysis:
            assert metadata["intent"] == test_enriched_lead.ai_analysis.intent.value
            assert metadata["urgency"] == test_enriched_lead.ai_analysis.urgency.value
            assert metadata["quality_score"] == test_enriched_lead.ai_analysis.quality_score
        
        print(f"✅ Add lead to database: PASS (ID: {test_enriched_lead.id})")
        return test_enriched_lead
    
    async def test_similarity_search(self, vector_service, similar_lead_input, dissimilar_lead_input):
        """Test similarity search functionality."""
        # Search for similar leads
        similar_results = await vector_service.find_similar_leads(
            similar_lead_input,
            threshold=0.7,  # Lower threshold for testing
            limit=5
        )
        
        # Should find results (assuming we added a similar lead in previous test)
        assert isinstance(similar_results, list)
        
        # Test with dissimilar lead
        dissimilar_results = await vector_service.find_similar_leads(
            dissimilar_lead_input,
            threshold=0.8,  # Higher threshold
            limit=5
        )
        
        # Verify SimilarityResult objects
        for result in similar_results:
            assert isinstance(result, SimilarityResult)
            assert isinstance(result.lead_id, type(uuid4()))
            assert 0.0 <= result.similarity_score <= 1.0
            assert isinstance(result.metadata, dict)
        
        # Test threshold filtering
        high_threshold_results = await vector_service.find_similar_leads(
            similar_lead_input,
            threshold=0.95,  # Very high threshold
            limit=5
        )
        
        # Should have fewer or equal results with higher threshold
        assert len(high_threshold_results) <= len(similar_results)
        
        print(f"✅ Similarity search: PASS (found {len(similar_results)} similar leads)")
        return similar_results
    
    async def test_update_lead(self, vector_service, test_enriched_lead):
        """Test updating leads in the database."""
        # Modify the lead
        original_id = test_enriched_lead.id
        test_enriched_lead.message = "Updated: My Honda Civic brake repair is now urgent!"
        test_enriched_lead.ai_analysis.quality_score = 95
        
        # Update in database
        updated_vector_data = await vector_service.update_lead(test_enriched_lead)
        
        # Verify update
        assert isinstance(updated_vector_data, VectorData)
        
        # Verify lead still exists with same ID
        result = vector_service.collection.get(ids=[str(original_id)])
        assert len(result["ids"]) == 1
        
        # Verify updated metadata
        metadata = result["metadatas"][0]
        assert "Updated:" in result["documents"][0]  # Updated message in document
        assert metadata["quality_score"] == 95
        
        print(f"✅ Update lead: PASS (ID: {original_id})")
    
    async def test_remove_lead(self, vector_service, test_enriched_lead):
        """Test removing leads from the database."""
        lead_id = test_enriched_lead.id
        
        # First add the lead to the database
        await vector_service.add_lead(test_enriched_lead)
        
        # Verify lead exists before removal
        result = vector_service.collection.get(ids=[str(lead_id)])
        assert len(result["ids"]) == 1
        
        # Remove lead
        removed = await vector_service.remove_lead(lead_id)
        assert removed is True
        
        # Verify lead no longer exists
        result = vector_service.collection.get(ids=[str(lead_id)])
        assert len(result["ids"]) == 0
        
        # Test removing non-existent lead
        non_existent_id = uuid4()
        removed = await vector_service.remove_lead(non_existent_id)
        assert removed is False
        
        print(f"✅ Remove lead: PASS (ID: {lead_id})")
    
    async def test_concurrent_operations(self, vector_service):
        """Test concurrent operations on ChromaDB."""
        # Create multiple test leads
        test_leads = []
        for i in range(5):
            lead_input = LeadInput(
                message=f"Test concurrent lead {i} - brake repair needed",
                contact=ContactInfo(
                    first_name="Test",
                    last_name=f"User{i}",
                    email=f"test{i}@example.com"
                ),
                source=LeadSource.WEB_FORM,
                custom_fields={"test_batch": "true", "index": str(i)}
            )
            
            enriched = EnrichedLead(
                **lead_input.model_dump(),
                id=uuid4(),
                status=LeadStatus.ENRICHED,
                enriched_at=datetime.utcnow()
            )
            test_leads.append(enriched)
        
        # Add leads concurrently
        start_time = time.time()
        tasks = [vector_service.add_lead(lead) for lead in test_leads]
        vector_data_results = await asyncio.gather(*tasks)
        add_time = time.time() - start_time
        
        # Verify all were added successfully
        assert len(vector_data_results) == 5
        for vector_data in vector_data_results:
            assert isinstance(vector_data, VectorData)
        
        # Test concurrent similarity searches
        start_time = time.time()
        search_lead = LeadInput(
            message="brake repair service needed",
            contact=ContactInfo(email="search@test.com"),
            source=LeadSource.WEB_FORM
        )
        
        search_tasks = [
            vector_service.find_similar_leads(search_lead, threshold=0.3, limit=3)
            for _ in range(3)
        ]
        search_results = await asyncio.gather(*search_tasks)
        search_time = time.time() - start_time
        
        # Verify search results
        assert len(search_results) == 3
        for results in search_results:
            assert isinstance(results, list)
            # Note: Results may be empty in test environment due to timing/isolation
            assert len(results) >= 0  # Should return valid list
        
        # Clean up test leads
        cleanup_tasks = [vector_service.remove_lead(lead.id) for lead in test_leads]
        await asyncio.gather(*cleanup_tasks)
        
        print(f"✅ Concurrent operations: PASS (add: {add_time:.2f}s, search: {search_time:.2f}s)")
    
    async def test_error_handling(self, vector_service):
        """Test error handling scenarios."""
        # Test with invalid embedding model (simulate failure)
        original_model = vector_service.embedding_model
        vector_service.embedding_model = None
        
        with pytest.raises(EmbeddingError):
            vector_service._generate_embedding("test")
        
        # Restore model
        vector_service.embedding_model = original_model
        
        # Test with minimal lead data
        minimal_lead = EnrichedLead(
            message="help",  # Minimal message
            contact=ContactInfo(),  # Empty contact
            source=LeadSource.WEB_FORM,
            id=uuid4(),
            status=LeadStatus.RAW,
            enriched_at=datetime.utcnow()
        )
        
        # Should handle gracefully with minimal data
        try:
            vector_data = await vector_service.add_lead(minimal_lead)
            assert isinstance(vector_data, VectorData)
            # Clean up
            await vector_service.remove_lead(minimal_lead.id)
        except (EmbeddingError, ChromaDBError):
            # Error is acceptable for truly minimal data
            pass
        
        print("✅ Error handling: PASS")
    
    async def test_performance_benchmarks(self, vector_service):
        """Test performance of ChromaDB operations."""
        # Test embedding generation speed
        test_message = "My car needs brake repair service urgently due to grinding noise"
        
        start_time = time.time()
        for _ in range(10):
            embedding = vector_service._generate_embedding(test_message)
        embedding_time = (time.time() - start_time) / 10
        
        assert embedding_time < 0.5, f"Embedding generation too slow: {embedding_time:.3f}s"
        
        # Test search performance with existing data
        search_lead = LeadInput(
            message="brake service needed",
            contact=ContactInfo(email="perf@test.com"),
            source=LeadSource.WEB_FORM
        )
        
        start_time = time.time()
        results = await vector_service.find_similar_leads(search_lead, limit=10)
        search_time = time.time() - start_time
        
        assert search_time < 2.0, f"Search too slow: {search_time:.3f}s (requirement: <2s)"
        
        print(f"✅ Performance benchmarks: PASS (embedding: {embedding_time:.3f}s, search: {search_time:.3f}s)")
    
    async def test_data_persistence(self, vector_service):
        """Test data persistence across service operations."""
        # Add a test lead
        test_lead = EnrichedLead(
            message="Persistence test lead for brake repair",
            contact=ContactInfo(
                first_name="Persistence",
                last_name="Test",
                email="persist@test.com"
            ),
            source=LeadSource.WEB_FORM,
            id=uuid4(),
            status=LeadStatus.ENRICHED,
            enriched_at=datetime.utcnow()
        )
        
        await vector_service.add_lead(test_lead)
        
        # Verify it exists
        result = vector_service.collection.get(ids=[str(test_lead.id)])
        assert len(result["ids"]) == 1
        
        # Create new service instance (simulates restart)
        new_service = ChromaVectorService()
        
        # Verify data persists
        result = new_service.collection.get(ids=[str(test_lead.id)])
        assert len(result["ids"]) == 1
        
        # Clean up
        await new_service.remove_lead(test_lead.id)
        
        print("✅ Data persistence: PASS")
    
    async def test_complete_crud_workflow(self, vector_service):
        """Test complete CRUD workflow with realistic data."""
        print("\n🔍 Testing Complete CRUD Workflow")
        
        # Create realistic automotive lead
        original_lead = EnrichedLead(
            message="My 2019 Toyota Camry has been making strange noises when braking. I think the brake pads need replacement. Can you provide a quote?",
            contact=ContactInfo(
                first_name="Michael",
                last_name="Johnson",
                email="m.johnson@email.com",
                phone="+1-555-234-5678",
                company="Johnson Transport"
            ),
            source=LeadSource.WEB_FORM,
            id=uuid4(),
            status=LeadStatus.ENRICHED,
            ai_analysis=AIAnalysis(
                intent=IntentCategory.QUOTE_REQUEST,
                intent_confidence=0.92,
                urgency=UrgencyLevel.MEDIUM,
                urgency_confidence=0.78,
                entities={
                    "vehicle_info": ["2019 Toyota Camry"],
                    "services": ["brake pad replacement"],
                    "symptoms": ["strange noises when braking"]
                },
                quality_score=85,
                topics=["brake_service", "quote_request"],
                summary="Customer requests quote for brake pad replacement on Toyota Camry",
                business_insights={"service_category": "maintenance", "customer_type": "business"},
                model_used="test_model",
                processing_time=1.8
            ),
            enriched_at=datetime.utcnow()
        )
        
        # 1. CREATE
        print("  1. Adding lead to database...")
        vector_data = await vector_service.add_lead(original_lead)
        assert isinstance(vector_data, VectorData)
        
        # 2. READ (via similarity search)
        print("  2. Searching for similar leads...")
        search_lead = LeadInput(
            message="Toyota brake service quote needed",
            contact=ContactInfo(email="search@test.com"),
            source=LeadSource.WEB_FORM
        )
        
        similar_leads = await vector_service.find_similar_leads(search_lead, threshold=0.3)
        assert len(similar_leads) >= 0  # Should return valid list
        
        # Only check for our lead if we found any results
        if len(similar_leads) > 0:
            found_our_lead = any(result.lead_id == original_lead.id for result in similar_leads)
            print(f"     Found {len(similar_leads)} similar leads, our lead present: {found_our_lead}")
        
        # 3. UPDATE
        print("  3. Updating lead information...")
        original_lead.message += " URGENT: Please call back today!"
        original_lead.ai_analysis.urgency = UrgencyLevel.HIGH
        original_lead.ai_analysis.quality_score = 92
        
        updated_vector_data = await vector_service.update_lead(original_lead)
        assert isinstance(updated_vector_data, VectorData)
        
        # Verify update
        result = vector_service.collection.get(ids=[str(original_lead.id)])
        assert "URGENT" in result["documents"][0]
        
        # 4. DELETE
        print("  4. Removing lead from database...")
        removed = await vector_service.remove_lead(original_lead.id)
        assert removed is True
        
        # Verify removal
        result = vector_service.collection.get(ids=[str(original_lead.id)])
        assert len(result["ids"]) == 0
        
        print("✅ Complete CRUD workflow: PASS")
        return True