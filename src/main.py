"""FastAPI application entry point for baseCamp."""

import logging
import sys
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from src.config.settings import settings


# Configure logging
def setup_logging():
    """Configure application logging."""
    log_config = {
        "level": getattr(logging, settings.log_level),
        "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        "handlers": [logging.StreamHandler(sys.stdout)],
    }
    
    if settings.log_format == "json":
        # In production, you might want to use structured logging like structlog
        pass
    
    logging.basicConfig(**log_config)
    
    # Set external library log levels
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)


# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    setup_logging()
    logger = logging.getLogger(__name__)
    logger.info("Starting baseCamp application")
    logger.info(f"Environment: {'development' if settings.is_development else 'production'}")
    logger.info(f"Ollama URL: {settings.ollama_base_url}")
    logger.info(f"ChromaDB directory: {settings.chroma_persist_directory}")
    logger.info(f"Airtable configured: {settings.airtable_configured}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down baseCamp application")


# Create FastAPI application
app = FastAPI(
    title="baseCamp API",
    description="AI-powered intake and CRM enrichment service for small businesses",
    version="0.1.0",
    docs_url=settings.get_docs_url(),
    redoc_url=settings.get_redoc_url(),
    lifespan=lifespan,
)

# Add rate limiter to app state
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)


@app.get("/", include_in_schema=False)
async def root() -> Dict[str, Any]:
    """Root endpoint redirect to docs."""
    return {
        "message": "baseCamp API",
        "version": "0.1.0",
        "docs_url": "/docs" if settings.enable_api_docs else None,
    }


@app.get("/api/v1/health")
@limiter.limit(f"{settings.rate_limit_requests_per_minute}/minute")
async def health_check(request) -> Dict[str, Any]:
    """Health check endpoint for monitoring service status."""
    logger = logging.getLogger(__name__)
    
    # Basic health status
    health_status = {
        "status": "healthy",
        "version": "0.1.0",
        "timestamp": None,
        "services": {
            "api": "healthy",
            "ollama": "unknown",
            "chromadb": "unknown",
            "airtable": "unknown" if settings.airtable_configured else "disabled",
        },
        "configuration": {
            "business_type": settings.business_type,
            "debug_mode": settings.debug,
            "airtable_enabled": settings.airtable_configured,
            "background_tasks_enabled": settings.enable_background_tasks,
        }
    }
    
    try:
        from datetime import datetime
        health_status["timestamp"] = datetime.utcnow().isoformat() + "Z"
        
        # TODO: Add actual service health checks when services are implemented
        # - Check Ollama connection
        # - Check ChromaDB connection
        # - Check Airtable connection (if configured)
        
        logger.info("Health check completed", extra={"status": "healthy"})
        return health_status
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        health_status["status"] = "unhealthy"
        health_status["error"] = str(e)
        return JSONResponse(
            status_code=503,
            content=health_status
        )


@app.get("/api/v1/config", include_in_schema=settings.is_development)
async def get_config() -> Dict[str, Any]:
    """Get application configuration (development only)."""
    if not settings.is_development:
        return JSONResponse(
            status_code=404,
            content={"detail": "Not found"}
        )
    
    # Return safe configuration (no secrets)
    return {
        "api_host": settings.api_host,
        "api_port": settings.api_port,
        "debug": settings.debug,
        "business_type": settings.business_type,
        "ollama_base_url": settings.ollama_base_url,
        "ollama_model": settings.ollama_model,
        "chroma_collection_name": settings.chroma_collection_name,
        "lead_similarity_threshold": settings.lead_similarity_threshold,
        "max_similar_leads": settings.max_similar_leads,
        "airtable_configured": settings.airtable_configured,
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "src.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.reload_on_change,
        log_level=settings.log_level.lower(),
    )