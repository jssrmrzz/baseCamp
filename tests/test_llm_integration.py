"""Integration tests for LLM service with real Ollama instance."""

import asyncio
import json
import pytest
import time
from typing import Dict, List

from src.models.lead import (
    AIAnalysis,
    ContactInfo,
    IntentCategory,
    LeadInput,
    LeadSource,
    UrgencyLevel
)
from src.services.llm_service import (
    OllamaService,
    LLMConnectionError,
    LLMTimeoutError,
    create_llm_service
)
from src.config.settings import settings


@pytest.mark.integration
@pytest.mark.asyncio
class TestLLMIntegration:
    """Integration tests for LLM service with real Ollama."""
    
    @pytest.fixture
    def llm_service(self):
        """Create real LLM service instance."""
        return OllamaService()
    
    @pytest.fixture
    def automotive_lead(self):
        """Sample automotive lead."""
        return LeadInput(
            message="My 2018 Honda Civic is making a grinding noise when I brake. It's getting worse and I'm worried about safety. Can I get an appointment this week?",
            contact=ContactInfo(
                full_name="John Smith",
                email="john.smith@email.com",
                phone="+1-555-123-4567"
            ),
            source=LeadSource.WEB_FORM,
            metadata={"form_id": "auto_repair_form"}
        )
    
    @pytest.fixture
    def medspa_lead(self):
        """Sample medspa lead."""
        return LeadInput(
            message="Hi, I'm interested in Botox for my forehead wrinkles. I have a wedding coming up in 6 weeks. What's the pricing and can we schedule a consultation?",
            contact=ContactInfo(
                full_name="Sarah Johnson",
                email="sarah.j@email.com"
            ),
            source=LeadSource.CHAT_WIDGET,
            metadata={"page": "botox_treatments"}
        )
    
    @pytest.fixture
    def consulting_lead(self):
        """Sample consulting lead."""
        return LeadInput(
            message="Our small manufacturing company needs help with process optimization. We're seeing bottlenecks in production and want to improve efficiency. Looking for a consultant with manufacturing experience.",
            contact=ContactInfo(
                full_name="Mike Rodriguez",
                email="m.rodriguez@mfgco.com",
                company="Rodriguez Manufacturing"
            ),
            source=LeadSource.REFERRAL,
            metadata={"industry": "manufacturing", "company_size": "50-100"}
        )
    
    @pytest.fixture
    def general_lead(self):
        """Sample general business lead."""
        return LeadInput(
            message="I need some help with my project. Can someone call me back?",
            contact=ContactInfo(
                full_name="Alex Taylor",
                phone="+1-555-987-6543"
            ),
            source=LeadSource.EMAIL,
            metadata={"subject": "Project Help Needed"}
        )
    
    async def test_service_health_check(self, llm_service):
        """Test Ollama service health check."""
        is_healthy = await llm_service.health_check()
        assert is_healthy, "Ollama service should be healthy and accessible"
    
    async def test_available_models(self, llm_service):
        """Test retrieving available models."""
        models = await llm_service.get_available_models()
        assert isinstance(models, list), "Should return list of models"
        assert len(models) > 0, "Should have at least one model available"
        assert "mistral:latest" in models, "Mistral model should be available"
    
    async def test_automotive_analysis(self, llm_service, automotive_lead):
        """Test automotive-specific lead analysis."""
        # Temporarily set business type for this test
        original_business_type = settings.business_type
        settings.business_type = "automotive"
        
        try:
            start_time = time.time()
            analysis = await llm_service.analyze_lead(automotive_lead)
            processing_time = time.time() - start_time
            
            # Validate response structure
            assert isinstance(analysis, AIAnalysis)
            assert analysis.model_used is not None
            assert analysis.processing_time > 0
            
            # Validate automotive-specific analysis
            assert analysis.intent in [
                IntentCategory.APPOINTMENT_REQUEST,
                IntentCategory.INQUIRY,
                IntentCategory.QUOTE_REQUEST
            ]
            assert analysis.intent_confidence > 0.5
            
            # Should detect high urgency due to safety concern
            assert analysis.urgency in [UrgencyLevel.HIGH, UrgencyLevel.URGENT]
            assert analysis.urgency_confidence > 0.5
            
            # Should identify vehicle and service entities
            entities = analysis.entities
            assert "vehicle_info" in entities or "services" in entities
            assert analysis.quality_score > 60  # Good quality lead
            
            # Performance requirement: < 5 seconds
            assert processing_time < 5.0, f"Processing took {processing_time:.2f}s, should be < 5s"
            
            print(f"✅ Automotive Analysis: {analysis.intent} (confidence: {analysis.intent_confidence:.2f}), "
                  f"Urgency: {analysis.urgency} (confidence: {analysis.urgency_confidence:.2f}), "
                  f"Quality: {analysis.quality_score}, Time: {processing_time:.2f}s")
            
        finally:
            settings.business_type = original_business_type
    
    async def test_medspa_analysis(self, llm_service, medspa_lead):
        """Test medspa-specific lead analysis."""
        original_business_type = settings.business_type
        settings.business_type = "medspa"
        
        try:
            start_time = time.time()
            analysis = await llm_service.analyze_lead(medspa_lead)
            processing_time = time.time() - start_time
            
            # Validate response structure
            assert isinstance(analysis, AIAnalysis)
            assert analysis.processing_time > 0
            
            # Should identify consultation/appointment intent
            assert analysis.intent in [
                IntentCategory.APPOINTMENT_REQUEST,
                IntentCategory.INQUIRY,
                IntentCategory.QUOTE_REQUEST
            ]
            
            # Should identify treatment entities
            entities = analysis.entities
            assert "treatments" in entities or "concerns" in entities or "timing" in entities
            
            # Should be high quality due to specific treatment request
            assert analysis.quality_score > 65
            
            # Performance check
            assert processing_time < 5.0
            
            print(f"✅ Medspa Analysis: {analysis.intent} (confidence: {analysis.intent_confidence:.2f}), "
                  f"Quality: {analysis.quality_score}, Time: {processing_time:.2f}s")
            
        finally:
            settings.business_type = original_business_type
    
    async def test_consulting_analysis(self, llm_service, consulting_lead):
        """Test consulting-specific lead analysis."""
        original_business_type = settings.business_type
        settings.business_type = "consulting"
        
        try:
            start_time = time.time()
            analysis = await llm_service.analyze_lead(consulting_lead)
            processing_time = time.time() - start_time
            
            # Validate response structure
            assert isinstance(analysis, AIAnalysis)
            
            # Should identify consulting-specific entities
            entities = analysis.entities
            assert any(key in entities for key in ["services", "industry", "company_size"])
            
            # Should have good quality score for detailed business inquiry
            assert analysis.quality_score > 70
            
            # Performance check
            assert processing_time < 5.0
            
            print(f"✅ Consulting Analysis: {analysis.intent} (confidence: {analysis.intent_confidence:.2f}), "
                  f"Quality: {analysis.quality_score}, Time: {processing_time:.2f}s")
            
        finally:
            settings.business_type = original_business_type
    
    async def test_general_analysis(self, llm_service, general_lead):
        """Test general business lead analysis."""
        original_business_type = settings.business_type
        settings.business_type = "general"
        
        try:
            start_time = time.time()
            analysis = await llm_service.analyze_lead(general_lead)
            processing_time = time.time() - start_time
            
            # Validate response structure
            assert isinstance(analysis, AIAnalysis)
            
            # Should handle vague inquiry appropriately
            assert analysis.intent == IntentCategory.GENERAL or analysis.intent == IntentCategory.INQUIRY
            
            # Lower quality due to vague message
            assert 20 <= analysis.quality_score <= 70
            
            # Performance check
            assert processing_time < 5.0
            
            print(f"✅ General Analysis: {analysis.intent} (confidence: {analysis.intent_confidence:.2f}), "
                  f"Quality: {analysis.quality_score}, Time: {processing_time:.2f}s")
            
        finally:
            settings.business_type = original_business_type
    
    async def test_concurrent_analysis(self, llm_service):
        """Test concurrent lead processing."""
        # Create multiple test leads
        leads = []
        for i in range(5):
            leads.append(LeadInput(
                message=f"Test message {i} - I need help with my project urgently.",
                contact=ContactInfo(
                    full_name=f"Test User {i}",
                    email=f"test{i}@example.com"
                ),
                source=LeadSource.REFERRAL,
                metadata={"test_batch": True, "index": i}
            ))
        
        # Process concurrently
        start_time = time.time()
        tasks = [llm_service.analyze_lead(lead) for lead in leads]
        analyses = await asyncio.gather(*tasks)
        total_time = time.time() - start_time
        
        # Validate all analyses completed
        assert len(analyses) == 5
        for analysis in analyses:
            assert isinstance(analysis, AIAnalysis)
            assert analysis.processing_time > 0
        
        # Should complete concurrent processing efficiently
        average_time_per_lead = total_time / len(leads)
        assert average_time_per_lead < 5.0, f"Average time per lead: {average_time_per_lead:.2f}s"
        
        print(f"✅ Concurrent Processing: {len(leads)} leads in {total_time:.2f}s "
              f"(avg: {average_time_per_lead:.2f}s per lead)")
    
    async def test_edge_cases(self, llm_service):
        """Test edge cases and error scenarios."""
        # Test empty message
        empty_lead = LeadInput(
            message="",
            contact=ContactInfo(email="test@example.com"),
            source=LeadSource.WEB_FORM
        )
        
        analysis = await llm_service.analyze_lead(empty_lead)
        assert isinstance(analysis, AIAnalysis)
        assert analysis.quality_score <= 50  # Low quality for empty message
        
        # Test very long message
        long_message = "Help me " * 500  # Very long repetitive message
        long_lead = LeadInput(
            message=long_message,
            contact=ContactInfo(email="test@example.com"),
            source=LeadSource.API
        )
        
        analysis = await llm_service.analyze_lead(long_lead)
        assert isinstance(analysis, AIAnalysis)
        
        # Test special characters
        special_lead = LeadInput(
            message="I need help with my café's événement spécial! ¿Cómo están? 日本語テスト",
            contact=ContactInfo(email="test@example.com"),
            source=LeadSource.CHAT_WIDGET
        )
        
        analysis = await llm_service.analyze_lead(special_lead)
        assert isinstance(analysis, AIAnalysis)
        
        print("✅ Edge cases handled successfully")
    
    async def test_json_response_consistency(self, llm_service):
        """Test that all responses produce valid, parseable JSON."""
        test_messages = [
            "I need an oil change appointment",
            "Botox consultation please",
            "Help with business strategy",
            "Emergency repair needed ASAP!",
            "Just checking prices"
        ]
        
        for message in test_messages:
            lead = LeadInput(
                message=message,
                contact=ContactInfo(email="test@example.com"),
                source=LeadSource.WEB_FORM
            )
            
            analysis = await llm_service.analyze_lead(lead)
            
            # Validate all required fields are present
            assert analysis.intent is not None
            assert 0.0 <= analysis.intent_confidence <= 1.0
            assert analysis.urgency is not None
            assert 0.0 <= analysis.urgency_confidence <= 1.0
            assert isinstance(analysis.entities, dict)
            assert 0 <= analysis.quality_score <= 100
            assert isinstance(analysis.topics, list)
            assert analysis.summary is not None
            assert isinstance(analysis.business_insights, dict)
        
        print("✅ JSON response consistency validated")
    
    async def test_performance_benchmark(self, llm_service):
        """Comprehensive performance benchmark."""
        test_cases = [
            ("Short query", "Help please"),
            ("Medium query", "I need help with my car's brake system. It's making noise."),
            ("Long query", "I'm looking for a comprehensive business consultation for my manufacturing company. We have several challenges including supply chain optimization, workforce efficiency, quality control improvements, and strategic planning for the next 3 years. Our company has about 75 employees and generates around $10M annually. We're particularly interested in lean manufacturing principles and digital transformation initiatives that could help us stay competitive in the market.")
        ]
        
        results = []
        for description, message in test_cases:
            lead = LeadInput(
                message=message,
                contact=ContactInfo(email="benchmark@test.com"),
                source=LeadSource.API
            )
            
            # Run multiple times for average
            times = []
            for _ in range(3):
                start_time = time.time()
                analysis = await llm_service.analyze_lead(lead)
                processing_time = time.time() - start_time
                times.append(processing_time)
            
            avg_time = sum(times) / len(times)
            results.append((description, avg_time, analysis.quality_score))
            
            # Validate performance requirement
            assert avg_time < 5.0, f"{description} took {avg_time:.2f}s, should be < 5s"
        
        print("📊 Performance Benchmark Results:")
        for description, avg_time, quality in results:
            print(f"   {description}: {avg_time:.2f}s (quality: {quality})")