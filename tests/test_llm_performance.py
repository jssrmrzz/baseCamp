"""Performance and validation tests for LLM service with real Ollama."""

import asyncio
import pytest
import time
from typing import List

from src.models.lead import ContactInfo, LeadInput, LeadSource
from src.services.llm_service import OllamaService
from src.config.settings import settings


@pytest.mark.asyncio
class TestLLMPerformance:
    """Performance validation tests for LLM service."""
    
    @pytest.fixture
    def llm_service(self):
        """Create real LLM service instance."""
        return OllamaService()
    
    async def test_basic_response_time(self, llm_service):
        """Test basic response time requirements."""
        lead = LeadInput(
            message="I need brake repair for my car ASAP",
            contact=ContactInfo(email="test@example.com"),
            source=LeadSource.WEB_FORM
        )
        
        start_time = time.time()
        analysis = await llm_service.analyze_lead(lead)
        processing_time = time.time() - start_time
        
        # Validate performance requirement: < 5 seconds
        assert processing_time < 5.0, f"Processing took {processing_time:.2f}s, should be < 5s"
        assert analysis.processing_time > 0
        assert analysis.model_used is not None
        
        print(f"✅ Basic response time: {processing_time:.2f}s")
    
    async def test_all_business_types(self, llm_service):
        """Test all 4 business type prompt templates."""
        business_types = ["general", "automotive", "medspa", "consulting"]
        original_business_type = settings.business_type
        
        results = {}
        
        try:
            for business_type in business_types:
                settings.business_type = business_type
                
                # Create appropriate test message for each business type
                messages = {
                    "general": "I need help with my project",
                    "automotive": "My car won't start, need urgent repair",
                    "medspa": "I need Botox consultation for my wedding",
                    "consulting": "Need business strategy consulting for growth"
                }
                
                lead = LeadInput(
                    message=messages[business_type],
                    contact=ContactInfo(email=f"test-{business_type}@example.com"),
                    source=LeadSource.WEB_FORM
                )
                
                start_time = time.time()
                analysis = await llm_service.analyze_lead(lead)
                processing_time = time.time() - start_time
                
                # Validate performance
                assert processing_time < 5.0, f"{business_type} took {processing_time:.2f}s"
                assert analysis.quality_score > 0
                assert analysis.intent is not None
                assert analysis.urgency is not None
                
                results[business_type] = {
                    "time": processing_time,
                    "quality": analysis.quality_score,
                    "intent": analysis.intent.value,
                    "urgency": analysis.urgency.value
                }
                
                print(f"✅ {business_type}: {processing_time:.2f}s, quality: {analysis.quality_score}")
        
        finally:
            settings.business_type = original_business_type
        
        # All business types should work
        assert len(results) == 4
        print(f"🎯 All 4 business types validated successfully")
    
    async def test_concurrent_processing(self, llm_service):
        """Test concurrent lead processing performance."""
        # Create 5 test leads
        leads = []
        for i in range(5):
            leads.append(LeadInput(
                message=f"Test urgent request {i} - need immediate assistance",
                contact=ContactInfo(email=f"concurrent-test-{i}@example.com"),
                source=LeadSource.WEB_FORM
            ))
        
        # Process concurrently
        start_time = time.time()
        tasks = [llm_service.analyze_lead(lead) for lead in leads]
        analyses = await asyncio.gather(*tasks)
        total_time = time.time() - start_time
        
        # Validate all completed successfully
        assert len(analyses) == 5
        for analysis in analyses:
            assert analysis.quality_score > 0
            assert analysis.intent is not None
        
        # Should handle concurrent processing efficiently
        average_time = total_time / len(leads)
        assert average_time < 5.0, f"Average time per lead: {average_time:.2f}s"
        
        print(f"✅ Concurrent processing: {len(leads)} leads in {total_time:.2f}s "
              f"(avg: {average_time:.2f}s per lead)")
    
    async def test_model_consistency(self, llm_service):
        """Test model response consistency."""
        lead = LeadInput(
            message="Emergency brake repair needed immediately",
            contact=ContactInfo(email="consistency@test.com"),
            source=LeadSource.WEB_FORM
        )
        
        # Run the same request 3 times
        analyses = []
        for i in range(3):
            analysis = await llm_service.analyze_lead(lead)
            analyses.append(analysis)
        
        # All should complete successfully
        for analysis in analyses:
            assert analysis.model_used == "mistral:latest"
            assert analysis.quality_score > 50  # Should recognize urgent brake repair
            assert analysis.processing_time > 0
        
        print(f"✅ Model consistency: 3 runs completed successfully")
    
    async def test_various_message_lengths(self, llm_service):
        """Test performance with various message lengths."""
        test_cases = [
            ("Short", "Help"),
            ("Medium", "I need brake repair for my 2018 Honda Civic"),
            ("Long", "I have a 2018 Honda Civic with 45,000 miles and recently I've been noticing some issues with the braking system. When I apply the brakes, especially during cold mornings, there's a grinding noise coming from the front wheels. The noise seems to get worse when I brake hard or when going downhill. I'm concerned this might be a safety issue and would like to schedule an appointment as soon as possible. I'm available weekdays after 3 PM or weekends. Please let me know what information you need and when you can fit me in.")
        ]
        
        results = []
        for length_type, message in test_cases:
            lead = LeadInput(
                message=message,
                contact=ContactInfo(email=f"{length_type.lower()}@test.com"),
                source=LeadSource.WEB_FORM
            )
            
            start_time = time.time()
            analysis = await llm_service.analyze_lead(lead)
            processing_time = time.time() - start_time
            
            # Validate performance regardless of message length
            assert processing_time < 5.0, f"{length_type} message took {processing_time:.2f}s"
            
            results.append((length_type, processing_time, analysis.quality_score))
            print(f"✅ {length_type} message ({len(message)} chars): {processing_time:.2f}s, "
                  f"quality: {analysis.quality_score}")
        
        # Longer messages should generally have higher quality scores
        assert results[2][2] >= results[0][2], "Long message should have higher quality than short"
    
    async def test_edge_case_handling(self, llm_service):
        """Test edge case handling performance."""
        edge_cases = [
            ("Empty contact", "", ContactInfo()),
            ("Special chars", "I need help with café service! ¿Cómo están?", ContactInfo(email="special@test.com")),
            ("Numbers only", "123 456 789", ContactInfo(phone="+1-555-123-4567")),
            ("Very urgent", "EMERGENCY!!! URGENT!!! HELP NOW!!!", ContactInfo(email="urgent@test.com"))
        ]
        
        for case_name, message, contact in edge_cases:
            lead = LeadInput(
                message=message,
                contact=contact,
                source=LeadSource.WEB_FORM
            )
            
            start_time = time.time()
            analysis = await llm_service.analyze_lead(lead)
            processing_time = time.time() - start_time
            
            # Should handle edge cases within performance limits
            assert processing_time < 5.0, f"{case_name} took {processing_time:.2f}s"
            assert analysis.quality_score >= 0
            
            print(f"✅ {case_name}: {processing_time:.2f}s")
    
    async def test_error_recovery(self, llm_service):
        """Test graceful error recovery."""
        # Test with potentially problematic input
        lead = LeadInput(
            message="Test message with potential JSON-breaking content: {\"broken\": json}",
            contact=ContactInfo(email="error-test@example.com"),
            source=LeadSource.WEB_FORM
        )
        
        start_time = time.time()
        analysis = await llm_service.analyze_lead(lead)
        processing_time = time.time() - start_time
        
        # Should still provide a response (even if fallback)
        assert analysis is not None
        assert processing_time < 5.0
        assert analysis.quality_score >= 0
        
        print(f"✅ Error recovery: {processing_time:.2f}s")