"""Lead intake API endpoints for baseCamp application."""

import logging
from typing import Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from ..config.settings import settings
from ..models.lead import EnrichedLead, LeadInput, LeadSummary
from ..services.llm_service import get_llm_service, LLMServiceInterface
from ..services.vector_service import get_vector_service, VectorServiceInterface, SimilarityResult
from ..services.airtable_service import get_crm_service, CRMServiceInterface


# Create router
router = APIRouter(prefix="/api/v1", tags=["intake"])

# Set up rate limiter
limiter = Limiter(key_func=get_remote_address)

# Logger
logger = logging.getLogger(__name__)




class IntakeResponse:
    """Response models for intake endpoints."""
    
    @staticmethod
    def success(
        lead_id: UUID, 
        message: str = "Lead processed successfully",
        similar_leads: Optional[List[Dict]] = None
    ) -> Dict:
        """Success response format."""
        response = {
            "success": True,
            "message": message,
            "lead_id": str(lead_id),
            "timestamp": None
        }
        
        if similar_leads:
            response["similar_leads"] = similar_leads
        
        # Add timestamp
        from datetime import datetime
        response["timestamp"] = datetime.utcnow().isoformat() + "Z"
        
        return response
    
    @staticmethod
    def error(message: str, details: Optional[Dict] = None) -> Dict:
        """Error response format."""
        response = {
            "success": False,
            "message": message,
            "timestamp": None
        }
        
        if details:
            response["details"] = details
        
        # Add timestamp
        from datetime import datetime
        response["timestamp"] = datetime.utcnow().isoformat() + "Z"
        
        return response


async def process_lead_pipeline(
    lead_input: LeadInput,
    llm_service: LLMServiceInterface,
    vector_service: VectorServiceInterface,
    crm_service: Optional[CRMServiceInterface] = None
) -> EnrichedLead:
    """Process lead through the complete enrichment pipeline."""
    
    # Create enriched lead from input
    enriched_lead = EnrichedLead(**lead_input.dict())
    enriched_lead.mark_processing()
    
    try:
        # Step 1: Check for similar leads (duplicate detection)
        logger.info(f"Checking for similar leads to {enriched_lead.id}")
        similar_leads = await vector_service.find_similar_leads(
            lead_input,
            threshold=settings.lead_similarity_threshold,
            limit=settings.max_similar_leads
        )
        
        if similar_leads:
            enriched_lead.similar_leads = [result.lead_id for result in similar_leads]
            logger.info(f"Found {len(similar_leads)} similar leads")
        
        # Step 2: LLM analysis for intent, urgency, and quality scoring
        logger.info(f"Analyzing lead {enriched_lead.id} with LLM")
        ai_analysis = await llm_service.analyze_lead(lead_input)
        enriched_lead.mark_enriched(ai_analysis)
        
        # Step 3: Generate and store vector embedding
        logger.info(f"Generating vector embedding for lead {enriched_lead.id}")
        vector_data = await vector_service.add_lead(enriched_lead)
        enriched_lead.vector_data = vector_data
        
        # Step 4: Sync to CRM (if enabled and configured)
        if crm_service and settings.airtable_configured:
            logger.info(f"Syncing lead {enriched_lead.id} to CRM")
            sync_result = await crm_service.sync_lead(enriched_lead)
            if sync_result.status.value == "success":
                enriched_lead.mark_synced("airtable", sync_result.airtable_record_id)
            else:
                logger.warning(f"CRM sync failed for lead {enriched_lead.id}: {sync_result.error_message}")
        
        logger.info(
            f"Lead {enriched_lead.id} processed successfully "
            f"(quality: {ai_analysis.quality_score}, intent: {ai_analysis.intent.value})"
        )
        
        return enriched_lead
        
    except Exception as e:
        error_msg = f"Pipeline processing failed: {str(e)}"
        logger.error(f"Error processing lead {enriched_lead.id}: {error_msg}")
        enriched_lead.mark_failed(error_msg)
        raise


async def process_lead_background(
    lead_input: LeadInput,
    llm_service: LLMServiceInterface,
    vector_service: VectorServiceInterface,
    crm_service: Optional[CRMServiceInterface] = None
):
    """Background task for processing leads."""
    try:
        enriched_lead = await process_lead_pipeline(
            lead_input, llm_service, vector_service, crm_service
        )
        logger.info(f"Background processing completed for lead {enriched_lead.id}")
    except Exception as e:
        logger.error(f"Background processing failed: {str(e)}")


@router.post("/intake")
@limiter.limit(f"{settings.rate_limit_requests_per_minute}/minute")
async def submit_lead(
    request: Request,
    lead_input: LeadInput,
    background_tasks: BackgroundTasks,
    llm_service: LLMServiceInterface = Depends(get_llm_service),
    vector_service: VectorServiceInterface = Depends(get_vector_service),
    crm_service: CRMServiceInterface = Depends(get_crm_service)
) -> JSONResponse:
    """
    Submit a new lead for processing.
    
    This endpoint accepts lead data from forms, chat widgets, or other sources,
    processes it through the AI enrichment pipeline, and stores it in the vector
    database and CRM system.
    
    The processing includes:
    1. Duplicate detection using vector similarity
    2. AI analysis for intent, urgency, and quality scoring
    3. Vector embedding generation and storage
    4. CRM synchronization (if configured)
    
    Returns immediately with lead ID while processing continues in background.
    """
    try:
        # Basic validation
        if not lead_input.message.strip():
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content=IntakeResponse.error("Message cannot be empty")
            )
        
        if not lead_input.contact.has_contact_method:
            logger.warning(f"Lead submitted without contact information: {lead_input.message[:50]}...")
        
        # Extract client IP for metadata if not provided
        if not lead_input.ip_address:
            lead_input.ip_address = get_remote_address(request)
        
        logger.info(f"New lead intake: {lead_input.message[:100]}...")
        
        # Create enriched lead for immediate response
        enriched_lead = EnrichedLead(**lead_input.dict())
        
        if settings.enable_background_tasks:
            # Process in background for faster response
            background_tasks.add_task(
                process_lead_background,
                lead_input,
                llm_service,
                vector_service,
                crm_service if settings.airtable_configured else None
            )
            
            return JSONResponse(
                status_code=status.HTTP_202_ACCEPTED,
                content=IntakeResponse.success(
                    enriched_lead.id,
                    "Lead received and queued for processing"
                )
            )
        else:
            # Process synchronously
            enriched_lead = await process_lead_pipeline(
                lead_input,
                llm_service,
                vector_service,
                crm_service if settings.airtable_configured else None
            )
            
            # Prepare similar leads info for response
            similar_leads_info = []
            if enriched_lead.similar_leads:
                similar_leads_info = [
                    {"lead_id": str(lead_id), "note": "Similar lead found"}
                    for lead_id in enriched_lead.similar_leads
                ]
            
            return JSONResponse(
                status_code=status.HTTP_201_CREATED,
                content=IntakeResponse.success(
                    enriched_lead.id,
                    "Lead processed successfully",
                    similar_leads_info if similar_leads_info else None
                )
            )
            
    except ValueError as e:
        logger.warning(f"Invalid lead data: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=IntakeResponse.error(f"Invalid lead data: {str(e)}")
        )
    except Exception as e:
        logger.error(f"Lead intake failed: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=IntakeResponse.error(
                "Internal server error processing lead",
                {"error_type": type(e).__name__}
            )
        )




@router.post("/intake/batch")
@limiter.limit(f"{int(settings.rate_limit_requests_per_minute / 2)}/minute")
async def submit_leads_batch(
    request: Request,
    leads: List[LeadInput],
    background_tasks: BackgroundTasks,
    llm_service: LLMServiceInterface = Depends(get_llm_service),
    vector_service: VectorServiceInterface = Depends(get_vector_service),
    crm_service: CRMServiceInterface = Depends(get_crm_service)
) -> JSONResponse:
    """
    Submit multiple leads for batch processing.
    
    Accepts up to 50 leads at once for efficient batch processing.
    All leads are processed in the background and results are not
    returned immediately.
    """
    try:
        # Validate batch size
        if len(leads) == 0:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content=IntakeResponse.error("Cannot process empty batch")
            )
        
        if len(leads) > 50:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content=IntakeResponse.error("Batch size cannot exceed 50 leads")
            )
        
        # Extract client IP for metadata
        client_ip = get_remote_address(request)
        for lead_input in leads:
            if not lead_input.ip_address:
                lead_input.ip_address = client_ip
        
        logger.info(f"Batch intake: {len(leads)} leads")
        
        # Create lead IDs for response
        lead_ids = []
        for lead_input in leads:
            enriched_lead = EnrichedLead(**lead_input.dict())
            lead_ids.append(enriched_lead.id)
        
        # Process all leads in background
        for lead_input in leads:
            background_tasks.add_task(
                process_lead_background,
                lead_input,
                llm_service,
                vector_service,
                crm_service if settings.airtable_configured else None
            )
        
        return JSONResponse(
            status_code=status.HTTP_202_ACCEPTED,
            content={
                "success": True,
                "message": f"{len(leads)} leads queued for processing",
                "lead_ids": [str(lead_id) for lead_id in lead_ids],
                "batch_size": len(leads),
                "timestamp": None
            }
        )
        
    except Exception as e:
        logger.error(f"Batch intake failed: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=IntakeResponse.error(
                "Internal server error processing batch",
                {"error_type": type(e).__name__}
            )
        )




@router.post("/intake/check-similar")
@limiter.limit(f"{settings.rate_limit_requests_per_minute * 2}/minute")
async def check_similar_leads(
    request: Request,
    lead_input: LeadInput,
    threshold: Optional[float] = None,
    limit: Optional[int] = None,
    vector_service: VectorServiceInterface = Depends(get_vector_service)
) -> JSONResponse:
    """
    Check for similar leads without processing.
    
    This endpoint allows checking for similar/duplicate leads
    without going through the full processing pipeline.
    Useful for real-time duplicate detection in forms.
    """
    try:
        # Use defaults if not provided
        threshold = threshold or settings.lead_similarity_threshold
        limit = limit or settings.max_similar_leads
        
        # Validate parameters
        if not 0.0 <= threshold <= 1.0:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content=IntakeResponse.error("Threshold must be between 0.0 and 1.0")
            )
        
        if not 1 <= limit <= 50:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content=IntakeResponse.error("Limit must be between 1 and 50")
            )
        
        logger.info(f"Similarity check for: {lead_input.message[:50]}...")
        
        # Find similar leads
        similar_results = await vector_service.find_similar_leads(
            lead_input, threshold, limit
        )
        
        # Format results
        similar_leads = []
        for result in similar_results:
            similar_leads.append({
                "lead_id": str(result.lead_id),
                "similarity_score": round(result.similarity_score, 3),
                "metadata": {
                    "message": result.metadata.get("message", "")[:100],
                    "source": result.metadata.get("source"),
                    "received_at": result.metadata.get("received_at"),
                    "quality_score": result.metadata.get("quality_score")
                }
            })
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "success": True,
                "message": f"Found {len(similar_leads)} similar leads",
                "similar_leads": similar_leads,
                "search_params": {
                    "threshold": threshold,
                    "limit": limit
                },
                "timestamp": None
            }
        )
        
    except Exception as e:
        logger.error(f"Similarity check failed: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=IntakeResponse.error(
                "Internal server error during similarity check",
                {"error_type": type(e).__name__}
            )
        )


@router.get("/intake/health")
async def intake_health_check(
    llm_service: LLMServiceInterface = Depends(get_llm_service),
    vector_service: VectorServiceInterface = Depends(get_vector_service),
    crm_service: CRMServiceInterface = Depends(get_crm_service)
) -> JSONResponse:
    """
    Health check for intake services.
    
    Checks the status of all services required for lead intake:
    - LLM service (Ollama)
    - Vector service (ChromaDB)
    - CRM service (Airtable) - if configured
    """
    try:
        health_status = {
            "intake_service": "healthy",
            "services": {},
            "timestamp": None
        }
        
        # Check LLM service
        try:
            llm_healthy = await llm_service.health_check()
            health_status["services"]["llm"] = "healthy" if llm_healthy else "unhealthy"
        except Exception as e:
            health_status["services"]["llm"] = f"error: {str(e)}"
        
        # Check vector service
        try:
            vector_healthy = await vector_service.health_check()
            health_status["services"]["vector"] = "healthy" if vector_healthy else "unhealthy"
        except Exception as e:
            health_status["services"]["vector"] = f"error: {str(e)}"
        
        # Check CRM service (if configured)
        if settings.airtable_configured:
            try:
                crm_healthy = await crm_service.health_check()
                health_status["services"]["crm"] = "healthy" if crm_healthy else "unhealthy"
            except Exception as e:
                health_status["services"]["crm"] = f"error: {str(e)}"
        else:
            health_status["services"]["crm"] = "disabled"
        
        # Determine overall status
        service_statuses = [
            status for status in health_status["services"].values() 
            if status not in ["disabled"]
        ]
        
        if all(status == "healthy" for status in service_statuses):
            overall_status = "healthy"
            status_code = status.HTTP_200_OK
        elif any("error" in str(status) for status in service_statuses):
            overall_status = "unhealthy"
            status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        else:
            overall_status = "degraded"
            status_code = status.HTTP_200_OK
        
        health_status["intake_service"] = overall_status
        
        # Add timestamp
        from datetime import datetime
        health_status["timestamp"] = datetime.utcnow().isoformat() + "Z"
        
        return JSONResponse(
            status_code=status_code,
            content=health_status
        )
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "intake_service": "error",
                "error": str(e),
                "timestamp": None
            }
        )


# Note: Rate limit exception handling should be added to the main app
# in src/main.py if needed