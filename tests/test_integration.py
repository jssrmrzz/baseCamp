"""Integration tests for baseCamp application."""

import asyncio
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from src.main import app
from src.config.settings import settings


@pytest.mark.integration
class TestApplicationStartup:
    """Test application startup and basic functionality."""
    
    def test_app_startup_success(self):
        """Test that the FastAPI application starts successfully."""
        # Test that the app object is created correctly
        assert app is not None
        assert app.title == "baseCamp API"
        assert app.version == "0.1.0"
    
    def test_app_routes_registered(self):
        """Test that all expected routes are registered."""
        # Get all routes from the app
        routes = [route.path for route in app.routes]
        
        # Core routes
        assert "/" in routes
        assert "/api/v1/health" in routes
        assert "/api/v1/config" in routes
        
        # Intake routes
        assert "/api/v1/intake" in routes
        assert "/api/v1/intake/batch" in routes
        assert "/api/v1/intake/check-similar" in routes
        assert "/api/v1/intake/health" in routes
        
        # Lead management routes
        assert "/api/v1/leads" in routes
        assert "/api/v1/leads/{lead_id}" in routes
        assert "/api/v1/leads/{lead_id}/similar" in routes
        assert "/api/v1/leads/stats/summary" in routes
        assert "/api/v1/leads/export" in routes
    
    def test_app_middleware_configured(self):
        """Test that middleware is properly configured."""
        # Check that CORS middleware is added
        middleware_types = [type(middleware) for middleware in app.user_middleware]
        from fastapi.middleware.cors import CORSMiddleware
        
        # CORS middleware should be present
        cors_middleware_present = any(
            "CORS" in str(middleware_type) for middleware_type in middleware_types
        )
        assert cors_middleware_present
    
    def test_openapi_schema_generation(self):
        """Test that OpenAPI schema is generated correctly."""
        with TestClient(app) as client:
            # Test that OpenAPI schema endpoint works
            response = client.get("/openapi.json")
            assert response.status_code == 200
            
            schema = response.json()
            assert schema["info"]["title"] == "baseCamp API"
            assert schema["info"]["version"] == "0.1.0"
    
    def test_docs_endpoint_available(self):
        """Test that API documentation is available."""
        with TestClient(app) as client:
            # Test Swagger UI
            response = client.get("/docs")
            assert response.status_code == 200
            
            # Test ReDoc
            response = client.get("/redoc")
            assert response.status_code == 200


@pytest.mark.integration
class TestBasicEndpointIntegration:
    """Test basic endpoint functionality without external services."""
    
    def test_root_endpoint_integration(self):
        """Test root endpoint with full application context."""
        with TestClient(app) as client:
            response = client.get("/")
            
            assert response.status_code == 200
            data = response.json()
            assert data["message"] == "baseCamp API"
            assert data["version"] == "0.1.0"
            
            # Should include docs URL in development
            if settings.enable_api_docs:
                assert data["docs_url"] is not None
    
    def test_health_endpoint_integration(self):
        """Test health endpoint with basic checks."""
        with TestClient(app) as client:
            response = client.get("/api/v1/health")
            
            # Should return 503 because external services aren't available
            # but the endpoint structure should be correct
            assert response.status_code in [200, 503]  # Either healthy or unhealthy
            
            data = response.json()
            assert "status" in data
            assert "version" in data
            assert "services" in data
            assert "configuration" in data
            
            # Check service status structure
            services = data["services"]
            assert "api" in services
            assert "ollama" in services  
            assert "chromadb" in services
            assert "airtable" in services
    
    def test_config_endpoint_integration(self):
        """Test configuration endpoint."""
        with TestClient(app) as client:
            response = client.get("/api/v1/config")
            
            if settings.is_development:
                assert response.status_code == 200
                data = response.json()
                
                # Should contain safe configuration values
                assert "api_host" in data
                assert "api_port" in data
                assert "debug" in data
                assert "business_type" in data
                assert "ollama_base_url" in data
                
                # Should not contain sensitive values
                assert "airtable_api_key" not in data
                assert "api_secret_key" not in data
            else:
                assert response.status_code == 404


@pytest.mark.integration
class TestErrorHandlingIntegration:
    """Test error handling with full application context."""
    
    def test_404_error_handling(self):
        """Test 404 error handling."""
        with TestClient(app) as client:
            response = client.get("/nonexistent/endpoint")
            assert response.status_code == 404
    
    def test_method_not_allowed(self):
        """Test method not allowed error."""
        with TestClient(app) as client:
            # POST to a GET-only endpoint
            response = client.post("/api/v1/health")
            assert response.status_code == 405
    
    def test_validation_error_integration(self):
        """Test validation error handling in real endpoint."""
        with TestClient(app) as client:
            # Send invalid JSON to intake endpoint
            response = client.post(
                "/api/v1/intake",
                json={"message": ""}  # Empty message should fail validation
            )
            
            assert response.status_code == 400
            data = response.json()
            assert data["success"] is False
            assert "message" in data


@pytest.mark.integration
class TestServiceIntegrationMocked:
    """Test service integration with mocked external dependencies."""
    
    @pytest.fixture
    def mock_external_services(self):
        """Mock all external service dependencies."""
        mocks = {}
        
        # Mock ChromaDB
        mocks['chromadb'] = patch('chromadb.PersistentClient')
        mocks['sentence_transformers'] = patch('sentence_transformers.SentenceTransformer')
        
        # Mock Airtable
        mocks['pyairtable'] = patch('pyairtable.Api')
        
        # Mock httpx for Ollama
        mocks['httpx'] = patch('httpx.AsyncClient')
        
        # Start all mocks
        for mock in mocks.values():
            mock.start()
        
        yield mocks
        
        # Stop all mocks
        for mock in mocks.values():
            mock.stop()
    
    def test_intake_with_mocked_services(self, mock_external_services):
        """Test intake endpoint with mocked external services."""
        with TestClient(app) as client:
            # Configure mocks to return successful responses
            with patch('src.services.llm_service.OllamaService.analyze_lead') as mock_analyze:
                with patch('src.services.vector_service.ChromaVectorService.add_lead') as mock_add_vector:
                    with patch('src.services.airtable_service.AirtableService.sync_lead') as mock_sync:
                        
                        # Configure mock returns
                        from src.models.lead import AIAnalysis, VectorData
                        from src.models.airtable import SyncRecord
                        from uuid import uuid4
                        
                        mock_analyze.return_value = AIAnalysis()
                        mock_add_vector.return_value = VectorData(
                            embedding=[0.1] * 384,
                            embedding_model="test",
                            text_hash="test"
                        )
                        sync_record = SyncRecord(
                            lead_id=uuid4(),
                            operation="create",
                            base_id="test",
                            table_name="test"
                        )
                        sync_record.mark_success("rec123")
                        mock_sync.return_value = sync_record
                        
                        # Make request
                        response = client.post(
                            "/api/v1/intake",
                            json={
                                "message": "Test integration message",
                                "contact": {
                                    "first_name": "Test",
                                    "email": "test@example.com"
                                }
                            }
                        )
                        
                        # Should accept the request for background processing
                        assert response.status_code in [201, 202]
                        data = response.json()
                        assert data["success"] is True
                        assert "lead_id" in data
    
    def test_similarity_check_integration(self, mock_external_services):
        """Test similarity check with mocked vector service."""
        with TestClient(app) as client:
            with patch('src.services.vector_service.ChromaVectorService.find_similar_leads') as mock_find:
                # Mock similarity results
                from src.services.vector_service import SimilarityResult
                from uuid import uuid4
                
                mock_find.return_value = [
                    SimilarityResult(
                        lead_id=uuid4(),
                        similarity_score=0.95,
                        metadata={"message": "Similar message"}
                    )
                ]
                
                response = client.post(
                    "/api/v1/intake/check-similar",
                    json={
                        "message": "Test similarity check",
                        "contact": {"email": "test@example.com"}
                    }
                )
                
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert len(data["similar_leads"]) == 1


@pytest.mark.integration
@pytest.mark.slow
class TestPerformanceIntegration:
    """Test application performance characteristics."""
    
    def test_app_startup_time(self):
        """Test that application starts within reasonable time."""
        import time
        
        start_time = time.time()
        
        # Create test client (triggers app startup)
        with TestClient(app) as client:
            # Make a simple request
            response = client.get("/")
            assert response.status_code == 200
        
        startup_time = time.time() - start_time
        
        # Should start in less than 5 seconds
        assert startup_time < 5.0
    
    def test_concurrent_requests(self):
        """Test handling of concurrent requests."""
        import threading
        import time
        
        results = []
        
        def make_request():
            with TestClient(app) as client:
                response = client.get("/api/v1/health")
                results.append(response.status_code)
        
        # Start multiple threads
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
            thread.start()
        
        # Wait for all to complete
        for thread in threads:
            thread.join()
        
        # All requests should complete successfully
        assert len(results) == 10
        assert all(status in [200, 503] for status in results)  # Healthy or unhealthy


@pytest.mark.integration
class TestSettingsIntegration:
    """Test settings integration with application."""
    
    def test_settings_loaded_correctly(self):
        """Test that settings are loaded and accessible."""
        # Settings should be available
        assert settings is not None
        
        # Test settings values are reasonable
        assert settings.api_port > 0
        assert settings.api_host is not None
        assert settings.ollama_base_url.startswith("http")
        assert settings.rate_limit_requests_per_minute > 0
    
    def test_environment_specific_behavior(self):
        """Test environment-specific application behavior."""
        if settings.is_development:
            # Development mode should have docs enabled
            assert settings.enable_api_docs is True
            
            # Config endpoint should be available
            with TestClient(app) as client:
                response = client.get("/api/v1/config")
                assert response.status_code == 200
        
        if settings.is_production:
            # Production mode might have docs disabled
            # and other production-specific settings
            pass  # Would test production-specific behavior


if __name__ == "__main__":
    pytest.main([__file__])