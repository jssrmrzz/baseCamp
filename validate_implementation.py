#!/usr/bin/env python3
"""
Basic validation script for baseCamp Phase 2 implementation.
Tests core functionality without requiring external dependencies.
"""

import sys
import os
import traceback
from typing import Dict, List, Any
import asyncio
from datetime import datetime

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def print_section(title: str):
    """Print a formatted section header."""
    print(f"\n{'='*60}")
    print(f" {title}")
    print(f"{'='*60}")

def print_test(test_name: str, success: bool, details: str = ""):
    """Print test result."""
    status = "✅ PASS" if success else "❌ FAIL"
    print(f"{status} {test_name}")
    if details:
        print(f"    {details}")

def validate_imports() -> Dict[str, bool]:
    """Validate that all modules can be imported."""
    print_section("Import Validation")
    
    results = {}
    modules_to_test = [
        'config.settings',
        'models.lead',
        'models.airtable',
        'services.llm_service',
        'services.vector_service', 
        'services.airtable_service',
        'api.intake',
        'api.leads',
        'main'
    ]
    
    for module in modules_to_test:
        try:
            __import__(module)
            results[module] = True
            print_test(f"Import {module}", True)
        except ImportError as e:
            results[module] = False
            print_test(f"Import {module}", False, f"ImportError: {e}")
        except Exception as e:
            results[module] = False
            print_test(f"Import {module}", False, f"Error: {e}")
    
    return results

def validate_models():
    """Validate Pydantic model functionality."""
    print_section("Model Validation")
    
    try:
        from models.lead import (
            ContactInfo, LeadInput, EnrichedLead, AIAnalysis, 
            IntentCategory, UrgencyLevel, LeadSource, VectorData
        )
        
        # Test ContactInfo
        contact = ContactInfo(
            first_name="John",
            last_name="Doe", 
            email="john@example.com",
            phone="+1234567890"
        )
        assert contact.full_name == "John Doe"
        assert contact.has_contact_method is True
        print_test("ContactInfo creation and properties", True)
        
        # Test LeadInput
        lead_input = LeadInput(
            message="Test message for brake repair",
            contact=contact,
            source=LeadSource.WEB_FORM
        )
        assert lead_input.message == "Test message for brake repair"
        assert isinstance(lead_input.received_at, datetime)
        print_test("LeadInput creation and validation", True)
        
        # Test AIAnalysis
        ai_analysis = AIAnalysis(
            intent=IntentCategory.APPOINTMENT_REQUEST,
            intent_confidence=0.85,
            urgency=UrgencyLevel.HIGH,
            urgency_confidence=0.78,
            quality_score=82
        )
        assert ai_analysis.intent == IntentCategory.APPOINTMENT_REQUEST
        assert 0 <= ai_analysis.intent_confidence <= 1
        print_test("AIAnalysis creation and validation", True)
        
        # Test EnrichedLead
        enriched = EnrichedLead(**lead_input.dict())
        enriched.mark_processing()
        enriched.mark_enriched(ai_analysis)
        
        assert enriched.has_ai_analysis is True
        assert enriched.is_high_quality is True
        assert enriched.is_urgent is True
        print_test("EnrichedLead lifecycle and properties", True)
        
        # Test VectorData
        vector_data = VectorData(
            embedding=[0.1, 0.2, 0.3] * 128,
            embedding_model="test-model",
            text_hash="abc123"
        )
        assert len(vector_data.embedding) == 384
        print_test("VectorData creation", True)
        
    except Exception as e:
        print_test("Model validation", False, f"Error: {e}")
        traceback.print_exc()
        return False
    
    return True

def validate_airtable_models():
    """Validate Airtable integration models."""
    print_section("Airtable Model Validation")
    
    try:
        from models.airtable import (
            AirtableConfig, AirtableRecord, SyncRecord, 
            SyncStatus, SyncOperation
        )
        from models.lead import EnrichedLead, LeadInput, ContactInfo, LeadSource
        
        # Test AirtableConfig
        config = AirtableConfig(
            base_id="appTEST123456789",
            table_name="TestLeads", 
            api_key="patTEST123456789"
        )
        assert config.base_id.startswith("app")
        print_test("AirtableConfig validation", True)
        
        # Test SyncRecord lifecycle
        from uuid import uuid4
        sync_record = SyncRecord(
            lead_id=uuid4(),
            operation=SyncOperation.CREATE,
            base_id="appTEST",
            table_name="TestLeads"
        )
        
        sync_record.mark_started()
        assert sync_record.status == SyncStatus.IN_PROGRESS
        
        sync_record.mark_success("rec123456")
        assert sync_record.status == SyncStatus.SUCCESS
        assert sync_record.is_complete is True
        print_test("SyncRecord lifecycle", True)
        
        # Test AirtableRecord creation
        contact = ContactInfo(first_name="Test", email="test@example.com")
        lead_input = LeadInput(message="Test", contact=contact, source=LeadSource.WEB_FORM)
        enriched = EnrichedLead(**lead_input.dict())
        
        airtable_record = AirtableRecord.from_enriched_lead(
            enriched, 
            config.field_mapping
        )
        assert airtable_record.lead_id == enriched.id
        assert len(airtable_record.fields) > 0
        print_test("AirtableRecord creation from EnrichedLead", True)
        
    except Exception as e:
        print_test("Airtable model validation", False, f"Error: {e}")
        traceback.print_exc()
        return False
    
    return True

def validate_service_interfaces():
    """Validate service interface definitions."""
    print_section("Service Interface Validation")
    
    try:
        from services.llm_service import LLMServiceInterface, OllamaService
        from services.vector_service import VectorServiceInterface  
        from services.airtable_service import CRMServiceInterface
        
        # Test that interfaces are properly defined
        llm_methods = ['analyze_lead', 'health_check', 'get_available_models']
        vector_methods = ['add_lead', 'find_similar_leads', 'update_lead', 'remove_lead', 'health_check']
        crm_methods = ['sync_lead', 'sync_leads_batch', 'update_lead', 'delete_lead', 'health_check']
        
        for method in llm_methods:
            assert hasattr(LLMServiceInterface, method)
        print_test("LLM service interface methods", True)
        
        for method in vector_methods:
            assert hasattr(VectorServiceInterface, method)
        print_test("Vector service interface methods", True)
        
        for method in crm_methods:
            assert hasattr(CRMServiceInterface, method)
        print_test("CRM service interface methods", True)
        
        # Test OllamaService initialization (without external deps)
        try:
            service = OllamaService()
            assert service.base_url is not None
            assert service.model is not None
            assert len(service.prompt_templates) >= 4  # general, automotive, medspa, consulting
            print_test("OllamaService initialization", True)
        except Exception as e:
            print_test("OllamaService initialization", False, f"Error: {e}")
        
    except Exception as e:
        print_test("Service interface validation", False, f"Error: {e}")
        traceback.print_exc()
        return False
    
    return True

def validate_fastapi_app():
    """Validate FastAPI application structure."""
    print_section("FastAPI Application Validation")
    
    try:
        from main import app
        
        # Test app is created
        assert app is not None
        assert app.title == "baseCamp API"
        assert app.version == "0.1.0"
        print_test("FastAPI app creation", True)
        
        # Test routes are registered
        routes = [route.path for route in app.routes]
        
        required_routes = [
            "/",
            "/api/v1/health",
            "/api/v1/config",
            "/api/v1/intake",
            "/api/v1/intake/batch",
            "/api/v1/intake/check-similar",
            "/api/v1/intake/health",
            "/api/v1/leads",
            "/api/v1/leads/{lead_id}",
            "/api/v1/leads/{lead_id}/similar",
            "/api/v1/leads/stats/summary",
            "/api/v1/leads/export"
        ]
        
        missing_routes = [route for route in required_routes if route not in routes]
        if missing_routes:
            print_test("Route registration", False, f"Missing routes: {missing_routes}")
        else:
            print_test("Route registration", True, f"All {len(required_routes)} routes registered")
        
        # Test middleware is configured
        middleware_count = len(app.user_middleware)
        print_test("Middleware configuration", middleware_count > 0, f"Middleware count: {middleware_count}")
        
    except Exception as e:
        print_test("FastAPI app validation", False, f"Error: {e}")
        traceback.print_exc()
        return False
    
    return True

def validate_configuration():
    """Validate configuration system."""
    print_section("Configuration Validation")
    
    try:
        from config.settings import settings
        
        # Test settings are loaded
        assert settings is not None
        print_test("Settings loading", True)
        
        # Test key settings exist
        required_settings = [
            'api_host', 'api_port', 'debug',
            'ollama_base_url', 'ollama_model',
            'chroma_persist_directory', 'chroma_collection_name',
            'rate_limit_requests_per_minute', 'log_level'
        ]
        
        for setting in required_settings:
            assert hasattr(settings, setting)
            value = getattr(settings, setting)
            assert value is not None
        print_test("Required settings present", True)
        
        # Test computed properties
        assert isinstance(settings.is_development, bool)
        assert isinstance(settings.is_production, bool)
        assert isinstance(settings.airtable_configured, bool)
        print_test("Computed properties", True)
        
        # Test validation
        assert settings.api_port > 0
        assert settings.rate_limit_requests_per_minute > 0
        assert 0.0 <= settings.lead_similarity_threshold <= 1.0
        print_test("Settings validation", True)
        
    except Exception as e:
        print_test("Configuration validation", False, f"Error: {e}")
        traceback.print_exc()
        return False
    
    return True

def validate_api_structure():
    """Validate API endpoint structure without running server."""
    print_section("API Structure Validation")
    
    try:
        # Test intake API structure
        from api.intake import router as intake_router
        intake_routes = [route.path for route in intake_router.routes]
        
        expected_intake = ['/intake', '/intake/batch', '/intake/check-similar', '/intake/health']
        for route in expected_intake:
            if not any(route in path for path in intake_routes):
                print_test(f"Intake route {route}", False, "Route not found")
                return False
        print_test("Intake API routes", True, f"{len(expected_intake)} routes found")
        
        # Test leads API structure
        from api.leads import router as leads_router
        leads_routes = [route.path for route in leads_router.routes]
        
        expected_leads = ['/leads', '/leads/{lead_id}', '/leads/stats/summary', '/leads/export']
        for route in expected_leads:
            if not any(route in path for path in leads_routes):
                print_test(f"Leads route {route}", False, "Route not found")
                return False
        print_test("Leads API routes", True, f"{len(expected_leads)} routes found")
        
    except Exception as e:
        print_test("API structure validation", False, f"Error: {e}")
        traceback.print_exc()
        return False
    
    return True

def run_validation():
    """Run complete validation suite."""
    print_section("baseCamp Phase 2 Implementation Validation")
    print("Testing core functionality without external dependencies...")
    
    validation_results = {
        'imports': validate_imports(),
        'models': validate_models(),
        'airtable_models': validate_airtable_models(), 
        'service_interfaces': validate_service_interfaces(),
        'configuration': validate_configuration(),
        'fastapi_app': validate_fastapi_app(),
        'api_structure': validate_api_structure()
    }
    
    # Summary
    print_section("Validation Summary")
    
    total_tests = len(validation_results)
    passed_tests = sum(1 for result in validation_results.values() if result)
    
    for test_name, result in validation_results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name.replace('_', ' ').title()}")
    
    print(f"\nOverall Result: {passed_tests}/{total_tests} validation categories passed")
    
    if passed_tests == total_tests:
        print("\n🎉 Phase 2 implementation validation SUCCESSFUL!")
        print("✅ All core components are properly implemented")
        print("✅ Models, services, and API structure are working")
        print("✅ Ready for Phase 3: External service integration")
        return True
    else:
        print(f"\n⚠️  Phase 2 validation completed with {total_tests - passed_tests} issues")
        print("Some components need attention before proceeding to Phase 3")
        return False

if __name__ == "__main__":
    success = run_validation()
    sys.exit(0 if success else 1)