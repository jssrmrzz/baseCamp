"""Prompt template validation and optimization tests."""

import asyncio
import json
import pytest
from typing import Dict, Any

from src.models.lead import ContactInfo, IntentCategory, LeadInput, LeadSource, UrgencyLevel
from src.services.llm_service import OllamaService
from src.config.settings import settings


@pytest.mark.asyncio 
class TestPromptValidation:
    """Validate prompt templates produce consistent, valid outputs."""
    
    @pytest.fixture
    def llm_service(self):
        """Create real LLM service instance."""
        return OllamaService()
    
    async def test_automotive_prompt_consistency(self, llm_service):
        """Test automotive prompt template produces consistent, valid JSON."""
        original_business_type = settings.business_type
        settings.business_type = "automotive"
        
        try:
            test_cases = [
                {
                    "message": "My 2018 Honda Civic brakes are squeaking badly. Need urgent repair.",
                    "expected_entities": ["vehicle_info", "services", "symptoms"],
                    "expected_urgency": [UrgencyLevel.HIGH, UrgencyLevel.URGENT],
                    "min_quality": 70
                },
                {
                    "message": "Oil change needed for my Toyota Camry next week",
                    "expected_entities": ["vehicle_info", "services"],
                    "expected_urgency": [UrgencyLevel.LOW, UrgencyLevel.MEDIUM],
                    "min_quality": 60
                },
                {
                    "message": "Car won't start at all! Emergency help needed immediately!",
                    "expected_entities": ["symptoms", "services"],
                    "expected_urgency": [UrgencyLevel.URGENT],
                    "min_quality": 75
                }
            ]
            
            for i, test_case in enumerate(test_cases):
                lead = LeadInput(
                    message=test_case["message"],
                    contact=ContactInfo(email=f"auto-test-{i}@example.com"),
                    source=LeadSource.WEB_FORM
                )
                
                analysis = await llm_service.analyze_lead(lead)
                
                # Validate structure
                assert analysis.intent is not None
                assert analysis.urgency in test_case["expected_urgency"]
                assert analysis.quality_score >= test_case["min_quality"]
                
                # Validate automotive-specific entities
                entities = analysis.entities
                entity_matches = sum(1 for key in test_case["expected_entities"] if key in entities)
                assert entity_matches >= 1, f"Should have at least one expected entity: {test_case['expected_entities']}"
                
                print(f"✅ Automotive case {i+1}: Intent={analysis.intent.value}, "
                      f"Urgency={analysis.urgency.value}, Quality={analysis.quality_score}")
        
        finally:
            settings.business_type = original_business_type
    
    async def test_medspa_prompt_consistency(self, llm_service):
        """Test medspa prompt template produces consistent, valid JSON."""
        original_business_type = settings.business_type
        settings.business_type = "medspa"
        
        try:
            test_cases = [
                {
                    "message": "I want Botox for my forehead wrinkles before my wedding next month",
                    "expected_entities": ["treatments", "concerns", "timing"],
                    "expected_intent": [IntentCategory.APPOINTMENT_REQUEST, IntentCategory.INQUIRY],
                    "min_quality": 75
                },
                {
                    "message": "Need a facial treatment consultation. First time client.",
                    "expected_entities": ["treatments", "experience_level"],
                    "expected_intent": [IntentCategory.APPOINTMENT_REQUEST, IntentCategory.INQUIRY],
                    "min_quality": 65
                },
                {
                    "message": "What are your prices for laser hair removal treatments?",
                    "expected_entities": ["treatments"],
                    "expected_intent": [IntentCategory.QUOTE_REQUEST, IntentCategory.INQUIRY],
                    "min_quality": 60
                }
            ]
            
            for i, test_case in enumerate(test_cases):
                lead = LeadInput(
                    message=test_case["message"],
                    contact=ContactInfo(email=f"medspa-test-{i}@example.com"),
                    source=LeadSource.WEB_FORM
                )
                
                analysis = await llm_service.analyze_lead(lead)
                
                # Validate structure
                assert analysis.intent in test_case["expected_intent"]
                assert analysis.quality_score >= test_case["min_quality"]
                
                # Validate medspa-specific entities
                entities = analysis.entities
                entity_matches = sum(1 for key in test_case["expected_entities"] if key in entities)
                assert entity_matches >= 1, f"Should have at least one expected entity: {test_case['expected_entities']}"
                
                print(f"✅ Medspa case {i+1}: Intent={analysis.intent.value}, "
                      f"Quality={analysis.quality_score}, Entities={list(entities.keys())}")
        
        finally:
            settings.business_type = original_business_type
    
    async def test_consulting_prompt_consistency(self, llm_service):
        """Test consulting prompt template produces consistent, valid JSON.""" 
        original_business_type = settings.business_type
        settings.business_type = "consulting"
        
        try:
            test_cases = [
                {
                    "message": "Need strategic consulting for our 50-person manufacturing company growth",
                    "expected_entities": ["services", "company_size", "industry"],
                    "expected_intent": [IntentCategory.INQUIRY, IntentCategory.QUOTE_REQUEST],
                    "min_quality": 80
                },
                {
                    "message": "Looking for HR consulting help with employee retention issues",
                    "expected_entities": ["services"],
                    "expected_intent": [IntentCategory.INQUIRY],
                    "min_quality": 70
                },
                {
                    "message": "Small business needs process optimization consulting immediately",
                    "expected_entities": ["services", "company_size"],
                    "expected_intent": [IntentCategory.INQUIRY, IntentCategory.APPOINTMENT_REQUEST],
                    "min_quality": 75
                }
            ]
            
            for i, test_case in enumerate(test_cases):
                lead = LeadInput(
                    message=test_case["message"],
                    contact=ContactInfo(email=f"consulting-test-{i}@example.com"),
                    source=LeadSource.WEB_FORM
                )
                
                analysis = await llm_service.analyze_lead(lead)
                
                # Validate structure
                assert analysis.intent in test_case["expected_intent"]
                assert analysis.quality_score >= test_case["min_quality"]
                
                # Validate consulting-specific entities
                entities = analysis.entities
                entity_matches = sum(1 for key in test_case["expected_entities"] if key in entities)
                assert entity_matches >= 1, f"Should have at least one expected entity: {test_case['expected_entities']}"
                
                print(f"✅ Consulting case {i+1}: Intent={analysis.intent.value}, "
                      f"Quality={analysis.quality_score}, Entities={list(entities.keys())}")
        
        finally:
            settings.business_type = original_business_type
    
    async def test_general_prompt_fallback(self, llm_service):
        """Test general prompt handles various business types appropriately."""
        original_business_type = settings.business_type
        settings.business_type = "general"
        
        try:
            test_cases = [
                "I need help with my project",
                "Emergency service required ASAP!",
                "What are your pricing options?",
                "Schedule a consultation please"
            ]
            
            for i, message in enumerate(test_cases):
                lead = LeadInput(
                    message=message,
                    contact=ContactInfo(email=f"general-test-{i}@example.com"),
                    source=LeadSource.WEB_FORM
                )
                
                analysis = await llm_service.analyze_lead(lead)
                
                # Should provide reasonable analysis even for vague requests
                assert analysis.intent is not None
                assert analysis.urgency is not None
                assert 20 <= analysis.quality_score <= 100
                assert isinstance(analysis.entities, dict)
                assert isinstance(analysis.topics, list)
                
                print(f"✅ General case {i+1}: Intent={analysis.intent.value}, "
                      f"Quality={analysis.quality_score}")
        
        finally:
            settings.business_type = original_business_type
    
    async def test_json_schema_compliance(self, llm_service):
        """Test that all responses strictly comply with expected JSON schema."""
        test_messages = [
            "Urgent brake repair needed for safety",
            "Botox consultation for wedding prep",
            "Business strategy consulting required",
            "General help request"
        ]
        
        business_types = ["automotive", "medspa", "consulting", "general"]
        original_business_type = settings.business_type
        
        try:
            for business_type in business_types:
                settings.business_type = business_type
                
                for i, message in enumerate(test_messages):
                    lead = LeadInput(
                        message=message,
                        contact=ContactInfo(email=f"schema-test-{business_type}-{i}@example.com"),
                        source=LeadSource.WEB_FORM
                    )
                    
                    analysis = await llm_service.analyze_lead(lead)
                    
                    # Validate all required fields and types
                    assert isinstance(analysis.intent, IntentCategory)
                    assert isinstance(analysis.intent_confidence, float)
                    assert 0.0 <= analysis.intent_confidence <= 1.0
                    
                    assert isinstance(analysis.urgency, UrgencyLevel)
                    assert isinstance(analysis.urgency_confidence, float)
                    assert 0.0 <= analysis.urgency_confidence <= 1.0
                    
                    assert isinstance(analysis.entities, dict)
                    for key, value in analysis.entities.items():
                        assert isinstance(key, str)
                        assert isinstance(value, list)
                        assert all(isinstance(item, str) for item in value)
                    
                    assert isinstance(analysis.quality_score, int)
                    assert 0 <= analysis.quality_score <= 100
                    
                    assert isinstance(analysis.topics, list)
                    assert all(isinstance(topic, str) for topic in analysis.topics)
                    
                    assert analysis.summary is None or isinstance(analysis.summary, str)
                    assert isinstance(analysis.business_insights, dict)
                    assert isinstance(analysis.model_used, str)
                    assert isinstance(analysis.processing_time, float)
                    
                    print(f"✅ Schema validation: {business_type} template")
        
        finally:
            settings.business_type = original_business_type
    
    async def test_confidence_score_calibration(self, llm_service):
        """Test that confidence scores are well-calibrated."""
        test_cases = [
            ("Very clear", "Emergency brake repair needed immediately for Honda Civic", 0.7),
            ("Somewhat clear", "Need car help soon", 0.4),
            ("Vague", "Help me please", 0.3),
            ("Detailed", "I need comprehensive business strategy consulting for my 75-employee manufacturing company to improve efficiency and growth planning", 0.8)
        ]
        
        for clarity, message, min_confidence in test_cases:
            lead = LeadInput(
                message=message,
                contact=ContactInfo(email=f"confidence-{clarity.lower().replace(' ', '-')}@test.com"),
                source=LeadSource.WEB_FORM
            )
            
            analysis = await llm_service.analyze_lead(lead)
            
            # More detailed messages should have higher confidence
            assert analysis.intent_confidence >= min_confidence, \
                f"{clarity} message should have confidence >= {min_confidence}, got {analysis.intent_confidence}"
            
            print(f"✅ {clarity}: Intent confidence = {analysis.intent_confidence:.2f}")
    
    async def test_concurrent_template_consistency(self, llm_service):
        """Test that different templates maintain consistency under concurrent load."""
        business_types = ["automotive", "medspa", "consulting", "general"]
        messages = {
            "automotive": "Emergency brake repair needed",
            "medspa": "Botox consultation needed",
            "consulting": "Business strategy help required", 
            "general": "Need assistance with project"
        }
        
        original_business_type = settings.business_type
        
        try:
            # Create concurrent tasks for different business types
            tasks = []
            for business_type in business_types:
                lead = LeadInput(
                    message=messages[business_type],
                    contact=ContactInfo(email=f"concurrent-{business_type}@test.com"),
                    source=LeadSource.WEB_FORM
                )
                
                # Create task that temporarily sets business type
                async def analyze_with_business_type(bt, ld):
                    settings.business_type = bt
                    return await llm_service.analyze_lead(ld)
                
                tasks.append(analyze_with_business_type(business_type, lead))
            
            # Execute all concurrently
            analyses = await asyncio.gather(*tasks)
            
            # Validate all completed successfully
            assert len(analyses) == 4
            for i, analysis in enumerate(analyses):
                business_type = business_types[i] 
                assert analysis.quality_score > 50
                assert analysis.intent is not None
                assert analysis.urgency is not None
                
                print(f"✅ Concurrent {business_type}: Quality={analysis.quality_score}")
        
        finally:
            settings.business_type = original_business_type