"""Lead management API endpoints for baseCamp application."""

import logging
from typing import Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.util import get_remote_address

from ..config.settings import settings
from ..models.lead import EnrichedLead, LeadQuery, LeadSummary, LeadStatus, IntentCategory, UrgencyLevel
from ..services.vector_service import get_vector_service, VectorServiceInterface


# Create router
router = APIRouter(prefix="/api/v1", tags=["leads"])

# Set up rate limiter
limiter = Limiter(key_func=get_remote_address)

# Logger
logger = logging.getLogger(__name__)


class LeadsResponse:
    """Response models for leads endpoints."""
    
    @staticmethod
    def success(data: Dict, message: str = "Success") -> Dict:
        """Success response format."""
        response = {
            "success": True,
            "message": message,
            "data": data,
            "timestamp": None
        }
        
        # Add timestamp
        from datetime import datetime, timezone
        response["timestamp"] = datetime.now(timezone.utc).isoformat()
        
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
        from datetime import datetime, timezone
        response["timestamp"] = datetime.now(timezone.utc).isoformat()
        
        return response


# Note: In a real implementation, you would have a proper database/storage layer
# For now, we'll use placeholder responses that show the expected API structure
class LeadStorage:
    """Placeholder lead storage interface."""
    
    @staticmethod
    async def get_lead(lead_id: UUID) -> Optional[EnrichedLead]:
        """Get a single lead by ID."""
        # This would query your actual database
        logger.warning("Lead storage not implemented - returning None")
        return None
    
    @staticmethod
    async def list_leads(query: LeadQuery) -> tuple[List[EnrichedLead], int]:
        """List leads with filtering and pagination."""
        # This would query your actual database
        logger.warning("Lead storage not implemented - returning empty list")
        return [], 0
    
    @staticmethod
    async def update_lead(lead_id: UUID, updates: Dict) -> Optional[EnrichedLead]:
        """Update a lead."""
        # This would update your actual database
        logger.warning("Lead storage not implemented - returning None")
        return None
    
    @staticmethod
    async def delete_lead(lead_id: UUID) -> bool:
        """Delete a lead."""
        # This would delete from your actual database
        logger.warning("Lead storage not implemented - returning False")
        return False


@router.get("/leads")
@limiter.limit(f"{settings.rate_limit_requests_per_minute}/minute")
async def list_leads(
    request: Request,
    # Pagination
    limit: int = Query(10, ge=1, le=100, description="Number of leads to return"),
    offset: int = Query(0, ge=0, description="Number of leads to skip"),
    
    # Filtering
    lead_status: Optional[LeadStatus] = Query(None, alias="status", description="Filter by lead status"),
    intent: Optional[IntentCategory] = Query(None, description="Filter by intent category"),
    urgency: Optional[UrgencyLevel] = Query(None, description="Filter by urgency level"),
    min_quality_score: Optional[int] = Query(None, ge=0, le=100, description="Minimum quality score"),
    max_quality_score: Optional[int] = Query(None, ge=0, le=100, description="Maximum quality score"),
    
    # Date filtering
    from_date: Optional[str] = Query(None, description="Filter from date (ISO format)"),
    to_date: Optional[str] = Query(None, description="Filter to date (ISO format)"),
    
    # Search
    search: Optional[str] = Query(None, max_length=200, description="Search in lead messages"),
    
    # Sorting
    sort_by: str = Query("received_at", description="Sort field"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$", description="Sort order")
) -> JSONResponse:
    """
    List leads with filtering, pagination, and search.
    
    Returns a paginated list of lead summaries with metadata.
    Supports filtering by status, intent, urgency, quality score, and date range.
    """
    try:
        # Parse dates
        parsed_from_date = None
        parsed_to_date = None
        
        if from_date:
            try:
                from datetime import datetime
                parsed_from_date = datetime.fromisoformat(from_date.replace('Z', '+00:00'))
            except ValueError:
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content=LeadsResponse.error("Invalid from_date format. Use ISO format.")
                )
        
        if to_date:
            try:
                from datetime import datetime
                parsed_to_date = datetime.fromisoformat(to_date.replace('Z', '+00:00'))
            except ValueError:
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content=LeadsResponse.error("Invalid to_date format. Use ISO format.")
                )
        
        # Create query object
        lead_query = LeadQuery(
            limit=limit,
            offset=offset,
            status=lead_status,
            intent=intent,
            urgency=urgency,
            min_quality_score=min_quality_score,
            max_quality_score=max_quality_score,
            from_date=parsed_from_date,
            to_date=parsed_to_date,
            search_query=search,
            sort_by=sort_by,
            sort_order=sort_order
        )
        
        logger.info(f"Listing leads with query: {lead_query.model_dump()}")
        
        # Get leads from storage
        leads, total_count = await LeadStorage.list_leads(lead_query)
        
        # Convert to summary format
        lead_summaries = [LeadSummary.from_enriched_lead(lead) for lead in leads]
        
        # Calculate pagination info
        has_next = (offset + limit) < total_count
        has_prev = offset > 0
        
        response_data = {
            "leads": [summary.model_dump(mode='json') for summary in lead_summaries],
            "pagination": {
                "total": total_count,
                "limit": limit,
                "offset": offset,
                "has_next": has_next,
                "has_prev": has_prev,
                "page": (offset // limit) + 1,
                "total_pages": (total_count + limit - 1) // limit
            },
            "filters": lead_query.model_dump(exclude_none=True)
        }
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=LeadsResponse.success(
                response_data,
                f"Retrieved {len(lead_summaries)} leads"
            )
        )
        
    except Exception as e:
        logger.error(f"Failed to list leads: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=LeadsResponse.error(
                "Internal server error listing leads",
                {"error_type": type(e).__name__}
            )
        )


@router.get("/leads/{lead_id}")
@limiter.limit(f"{settings.rate_limit_requests_per_minute}/minute")
async def get_lead(
    request: Request,
    lead_id: UUID
) -> JSONResponse:
    """
    Get a single lead by ID.
    
    Returns the complete lead information including AI analysis,
    vector data, and processing metadata.
    """
    try:
        logger.info(f"Getting lead {lead_id}")
        
        # Get lead from storage
        lead = await LeadStorage.get_lead(lead_id)
        
        if not lead:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content=LeadsResponse.error(f"Lead {lead_id} not found")
            )
        
        # Return complete lead data
        response_data = {
            "lead": lead.model_dump(mode='json')
        }
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=LeadsResponse.success(
                response_data,
                f"Retrieved lead {lead_id}"
            )
        )
        
    except ValueError:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=LeadsResponse.error("Invalid lead ID format")
        )
    except Exception as e:
        logger.error(f"Failed to get lead {lead_id}: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=LeadsResponse.error(
                "Internal server error retrieving lead",
                {"error_type": type(e).__name__}
            )
        )


@router.get("/leads/{lead_id}/similar")
@limiter.limit(f"{settings.rate_limit_requests_per_minute}/minute")
async def get_similar_leads(
    request: Request,
    lead_id: UUID,
    limit: int = Query(5, ge=1, le=20, description="Number of similar leads to return"),
    threshold: float = Query(0.8, ge=0.0, le=1.0, description="Similarity threshold"),
    vector_service: VectorServiceInterface = Depends(get_vector_service)
) -> JSONResponse:
    """
    Get leads similar to the specified lead.
    
    Uses vector similarity search to find leads with similar content.
    """
    try:
        logger.info(f"Finding similar leads to {lead_id}")
        
        # Get the original lead
        original_lead = await LeadStorage.get_lead(lead_id)
        if not original_lead:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content=LeadsResponse.error(f"Lead {lead_id} not found")
            )
        
        # Find similar leads using vector service
        similar_results = await vector_service.find_similar_leads(
            original_lead,
            threshold=threshold,
            limit=limit
        )
        
        # Format results
        similar_leads = []
        for result in similar_results:
            # Skip the original lead itself
            if result.lead_id == lead_id:
                continue
                
            similar_leads.append({
                "lead_id": str(result.lead_id),
                "similarity_score": round(result.similarity_score, 3),
                "metadata": {
                    "message": result.metadata.get("message", "")[:200],
                    "source": result.metadata.get("source"),
                    "status": result.metadata.get("status"),
                    "received_at": result.metadata.get("received_at"),
                    "quality_score": result.metadata.get("quality_score"),
                    "intent": result.metadata.get("intent"),
                    "urgency": result.metadata.get("urgency")
                }
            })
        
        response_data = {
            "original_lead_id": str(lead_id), 
            "similar_leads": similar_leads,
            "search_params": {
                "threshold": threshold,
                "limit": limit,
                "total_found": len(similar_leads)
            }
        }
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=LeadsResponse.success(
                response_data,
                f"Found {len(similar_leads)} similar leads"
            )
        )
        
    except ValueError:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=LeadsResponse.error("Invalid lead ID format")
        )
    except Exception as e:
        logger.error(f"Failed to find similar leads for {lead_id}: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=LeadsResponse.error(
                "Internal server error finding similar leads",
                {"error_type": type(e).__name__}
            )
        )


@router.put("/leads/{lead_id}")
@limiter.limit(f"{int(settings.rate_limit_requests_per_minute / 2)}/minute")
async def update_lead(
    request: Request,
    lead_id: UUID,
    updates: Dict
) -> JSONResponse:
    """
    Update a lead.
    
    Allows updating lead metadata, status, and other mutable fields.
    Cannot modify core content or AI analysis results.
    """
    try:
        logger.info(f"Updating lead {lead_id}")
        
        # Validate updates
        allowed_fields = {
            "status", "custom_fields", "source_url", "external_ids"
        }
        
        invalid_fields = set(updates.keys()) - allowed_fields
        if invalid_fields:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content=LeadsResponse.error(
                    f"Cannot update fields: {', '.join(invalid_fields)}",
                    {"allowed_fields": list(allowed_fields)}
                )
            )
        
        # Update lead in storage
        updated_lead = await LeadStorage.update_lead(lead_id, updates)
        
        if not updated_lead:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content=LeadsResponse.error(f"Lead {lead_id} not found")
            )
        
        response_data = {
            "lead": updated_lead.model_dump(mode='json'),
            "updated_fields": list(updates.keys())
        }
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=LeadsResponse.success(
                response_data,
                f"Lead {lead_id} updated successfully"
            )
        )
        
    except ValueError:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=LeadsResponse.error("Invalid lead ID format")
        )
    except Exception as e:
        logger.error(f"Failed to update lead {lead_id}: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=LeadsResponse.error(
                "Internal server error updating lead",
                {"error_type": type(e).__name__}
            )
        )


@router.delete("/leads/{lead_id}")
@limiter.limit(f"{int(settings.rate_limit_requests_per_minute / 4)}/minute")
async def delete_lead(
    request: Request,
    lead_id: UUID,
    vector_service: VectorServiceInterface = Depends(get_vector_service)
) -> JSONResponse:
    """
    Delete a lead.
    
    Removes the lead from storage, vector database, and external systems.
    This operation cannot be undone.
    """
    try:
        logger.info(f"Deleting lead {lead_id}")
        
        # Check if lead exists
        existing_lead = await LeadStorage.get_lead(lead_id)
        if not existing_lead:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content=LeadsResponse.error(f"Lead {lead_id} not found")
            )
        
        # Remove from vector database
        try:
            await vector_service.remove_lead(lead_id)
            logger.info(f"Removed lead {lead_id} from vector database")
        except Exception as e:
            logger.warning(f"Failed to remove lead {lead_id} from vector database: {str(e)}")
        
        # Remove from main storage
        deleted = await LeadStorage.delete_lead(lead_id)
        
        if not deleted:
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content=LeadsResponse.error("Failed to delete lead from storage")
            )
        
        response_data = {
            "deleted_lead_id": str(lead_id),
            "deletion_timestamp": None
        }
        
        # Add timestamp
        from datetime import datetime
        response_data["deletion_timestamp"] = datetime.now(timezone.utc).isoformat()
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=LeadsResponse.success(
                response_data,
                f"Lead {lead_id} deleted successfully"
            )
        )
        
    except ValueError:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=LeadsResponse.error("Invalid lead ID format")
        )
    except Exception as e:
        logger.error(f"Failed to delete lead {lead_id}: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=LeadsResponse.error(
                "Internal server error deleting lead",
                {"error_type": type(e).__name__}
            )
        )


@router.get("/leads/stats/summary")
@limiter.limit(f"{int(settings.rate_limit_requests_per_minute / 2)}/minute")
async def get_leads_summary_stats(
    request: Request,
    days: int = Query(7, ge=1, le=365, description="Number of days to include in stats")
) -> JSONResponse:
    """
    Get summary statistics for leads.
    
    Returns counts by status, intent, urgency, quality score ranges,
    and trends over the specified time period.
    """
    try:
        logger.info(f"Getting lead stats for last {days} days")
        
        # This would query your actual database for statistics
        # For now, return placeholder data
        stats_data = {
            "summary": {
                "total_leads": 0,
                "processed_leads": 0,
                "synced_leads": 0,
                "failed_leads": 0,
                "average_quality_score": 0.0,
                "period_days": days
            },
            "by_status": {
                "raw": 0,
                "processing": 0,
                "enriched": 0,
                "synced": 0,
                "failed": 0
            },
            "by_intent": {
                "inquiry": 0,
                "appointment_request": 0,
                "quote_request": 0,
                "support": 0,
                "complaint": 0,
                "general": 0
            },
            "by_urgency": {
                "low": 0,
                "medium": 0,
                "high": 0,
                "urgent": 0
            },
            "by_quality_score": {
                "high_quality": 0,      # 80-100
                "medium_quality": 0,    # 50-79
                "low_quality": 0        # 0-49
            },
            "daily_counts": [],  # List of {date, count} for trend analysis
            "top_sources": []    # List of {source, count}
        }
        
        response_data = {
            "stats": stats_data,
            "generated_at": None
        }
        
        # Add timestamp
        from datetime import datetime
        response_data["generated_at"] = datetime.now(timezone.utc).isoformat()
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=LeadsResponse.success(
                response_data,
                f"Lead statistics for last {days} days"
            )
        )
        
    except Exception as e:
        logger.error(f"Failed to get lead stats: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=LeadsResponse.error(
                "Internal server error retrieving stats",
                {"error_type": type(e).__name__}
            )
        )


@router.post("/leads/export")
@limiter.limit(f"{int(settings.rate_limit_requests_per_minute / 10)}/minute")
async def export_leads(
    request: Request,
    export_query: LeadQuery,
    format: str = Query("csv", pattern="^(csv|json)$", description="Export format")
) -> JSONResponse:
    """
    Export leads data.
    
    Exports leads matching the query criteria in CSV or JSON format.
    For large exports, this would typically return a job ID and process asynchronously.
    """
    try:
        logger.info(f"Exporting leads in {format} format")
        
        # For now, return a placeholder response
        # In a real implementation, this would:
        # 1. Query leads based on export_query
        # 2. Generate the export file
        # 3. Either return the file directly or create a background job
        
        response_data = {
            "export_status": "not_implemented",
            "message": "Export functionality not yet implemented",
            "requested_format": format,
            "query": export_query.model_dump(exclude_none=True)
        }
        
        return JSONResponse(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            content=LeadsResponse.error(
                "Export functionality not yet implemented",
                response_data
            )
        )
        
    except Exception as e:
        logger.error(f"Failed to export leads: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=LeadsResponse.error(
                "Internal server error during export",
                {"error_type": type(e).__name__}
            )
        )