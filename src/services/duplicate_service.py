"""Smart duplicate detection service for baseCamp application."""

import logging
from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Literal, Optional, Tuple
from uuid import UUID

from sentence_transformers import SentenceTransformer

from ..config.settings import settings
from ..models.lead import DuplicateStatus, EnrichedLead, LeadInput


class DuplicateAnalysisResult:
    """Result of duplicate analysis for a lead."""
    
    def __init__(
        self,
        action: Literal["process", "link", "flag", "merge"],
        reason: str,
        related_leads: List[UUID] = None,
        parent_lead_id: Optional[UUID] = None,
        customer_sequence: int = 1,
        time_since_last: Optional[int] = None,
        message_similarity: Optional[float] = None
    ):
        self.action = action
        self.reason = reason
        self.related_leads = related_leads or []
        self.parent_lead_id = parent_lead_id
        self.customer_sequence = customer_sequence
        self.time_since_last = time_since_last
        self.message_similarity = message_similarity
    
    def __repr__(self):
        return f"DuplicateAnalysisResult(action={self.action}, reason='{self.reason}')"


class DuplicateServiceInterface(ABC):
    """Abstract interface for duplicate detection services."""
    
    @abstractmethod
    async def analyze_lead_for_duplicates(
        self, 
        new_lead: LeadInput,
        contact_history: List[EnrichedLead]
    ) -> DuplicateAnalysisResult:
        """Analyze lead against contact history for duplicate handling."""
        pass
    
    @abstractmethod
    async def calculate_message_similarity(self, message1: str, message2: str) -> float:
        """Calculate semantic similarity between two messages."""
        pass
    
    @abstractmethod
    async def find_contact_history(
        self,
        contact_info,
        vector_service,
        time_window_hours: Optional[int] = None
    ) -> List[EnrichedLead]:
        """Find all previous leads from the same contact."""
        pass


class SmartDuplicateAnalyzer(DuplicateServiceInterface):
    """Smart duplicate analyzer implementing business logic for duplicate handling."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Configuration from settings
        self.duplicate_time_window_hours = getattr(settings, 'duplicate_time_window_hours', 24)
        self.duplicate_message_threshold = getattr(settings, 'duplicate_message_threshold', 0.8)
        self.duplicate_suspicious_threshold = getattr(settings, 'duplicate_suspicious_threshold', 0.9)
        self.duplicate_suspicious_window_minutes = getattr(settings, 'duplicate_suspicious_window_minutes', 60)
        self.allow_same_contact_multiple_leads = getattr(settings, 'allow_same_contact_multiple_leads', True)
        self.auto_link_related_leads = getattr(settings, 'auto_link_related_leads', True)
        self.flag_suspicious_duplicates = getattr(settings, 'flag_suspicious_duplicates', True)
        
        # Initialize embedding model for similarity calculation
        self.embedding_model = None
        self._initialize_embedding_model()
    
    def _initialize_embedding_model(self):
        """Initialize sentence transformer model for similarity calculations."""
        try:
            self.embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
            self.logger.info("Duplicate detection embedding model loaded successfully")
        except Exception as e:
            self.logger.error(f"Failed to load embedding model for duplicate detection: {str(e)}")
            self.embedding_model = None
    
    async def calculate_message_similarity(self, message1: str, message2: str) -> float:
        """Calculate semantic similarity between two messages."""
        try:
            if not self.embedding_model:
                self.logger.warning("Embedding model not available, using basic similarity")
                return self._basic_text_similarity(message1, message2)
            
            # Normalize messages
            msg1_norm = message1.strip().lower()
            msg2_norm = message2.strip().lower()
            
            # Generate embeddings
            embeddings = self.embedding_model.encode([msg1_norm, msg2_norm])
            
            # Calculate cosine similarity
            embedding1, embedding2 = embeddings[0], embeddings[1]
            dot_product = sum(a * b for a, b in zip(embedding1, embedding2))
            norm1 = sum(a * a for a in embedding1) ** 0.5
            norm2 = sum(a * a for a in embedding2) ** 0.5
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
            
            similarity = dot_product / (norm1 * norm2)
            return max(0.0, min(1.0, similarity))  # Clamp to [0, 1]
            
        except Exception as e:
            self.logger.error(f"Error calculating message similarity: {str(e)}")
            return self._basic_text_similarity(message1, message2)
    
    def _basic_text_similarity(self, message1: str, message2: str) -> float:
        """Basic text similarity fallback using word overlap."""
        words1 = set(message1.lower().split())
        words2 = set(message2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union)
    
    async def find_contact_history(
        self,
        contact_info,
        vector_service,
        time_window_hours: Optional[int] = None
    ) -> List[EnrichedLead]:
        """Find all previous leads from the same contact within time window."""
        try:
            # Create a dummy lead for contact matching
            dummy_lead = LeadInput(
                message="dummy", 
                contact=contact_info
            )
            
            # Get all similar leads (this will use contact-based matching)
            similar_results = await vector_service.find_similar_leads(
                dummy_lead,
                threshold=0.1,  # Very low threshold to catch all potential matches
                limit=50  # Reasonable limit for contact history
            )
            
            # Filter for same contact and time window
            contact_leads = []
            cutoff_time = None
            if time_window_hours:
                cutoff_time = datetime.utcnow() - timedelta(hours=time_window_hours)
            
            for result in similar_results:
                # Check if it's truly the same contact
                metadata = result.metadata
                if self._is_same_contact_from_metadata(contact_info, metadata):
                    # Check time window if specified
                    if cutoff_time and metadata.get('received_at'):
                        lead_time = datetime.fromisoformat(metadata['received_at'].replace('Z', '+00:00'))
                        if lead_time < cutoff_time:
                            continue
                    
                    # Create EnrichedLead from metadata (simplified)
                    contact_leads.append(result)
            
            self.logger.info(
                f"Found {len(contact_leads)} previous leads from same contact "
                f"(email: {contact_info.email}, phone: {contact_info.phone}, name: {contact_info.full_name})"
            )
            return contact_leads
            
        except Exception as e:
            self.logger.error(f"Error finding contact history: {str(e)}")
            return []
    
    def _is_same_contact_from_metadata(self, contact_info, metadata: Dict) -> bool:
        """Check if contact info matches stored metadata."""
        # Email match (most reliable)
        if contact_info.email and metadata.get("contact_email"):
            return str(contact_info.email).lower() == metadata["contact_email"].lower()
        
        # Phone match with normalization
        if contact_info.phone and metadata.get("contact_phone"):
            phone1 = "".join(c for c in contact_info.phone if c.isdigit())
            phone2 = "".join(c for c in metadata["contact_phone"] if c.isdigit())
            if len(phone1) >= 10 and len(phone2) >= 10:
                return phone1[-10:] == phone2[-10:]
        
        # Name match (less reliable)
        if contact_info.full_name and metadata.get("contact_name"):
            return contact_info.full_name.lower().strip() == metadata["contact_name"].lower().strip()
        
        return False
    
    async def analyze_lead_for_duplicates(
        self,
        new_lead: LeadInput,
        contact_history: List[EnrichedLead]
    ) -> DuplicateAnalysisResult:
        """Analyze lead against contact history for duplicate handling."""
        try:
            # If no contact history, this is the first lead from this contact
            if not contact_history:
                return DuplicateAnalysisResult(
                    action="process",
                    reason="First lead from this contact",
                    customer_sequence=1
                )
            
            # Sort contact history by received time (most recent first)
            def get_received_time(result):
                time_str = result.metadata.get('received_at', '1970-01-01T00:00:00Z')
                if time_str.endswith('Z'):
                    time_str = time_str[:-1] + '+00:00'
                try:
                    return datetime.fromisoformat(time_str)
                except (ValueError, TypeError):
                    return datetime(1970, 1, 1, tzinfo=timezone.utc)
            
            sorted_history = sorted(contact_history, key=get_received_time, reverse=True)
            
            # Safety check - this should not happen given the check above, but just in case
            if not sorted_history:
                return DuplicateAnalysisResult(
                    action="process",
                    reason="No valid contact history found",
                    customer_sequence=1
                )
            
            most_recent_lead = sorted_history[0]
            customer_sequence = len(contact_history) + 1
            
            # Calculate time since last lead
            last_lead_time_str = most_recent_lead.metadata.get('received_at', '1970-01-01T00:00:00Z')
            if last_lead_time_str.endswith('Z'):
                last_lead_time_str = last_lead_time_str[:-1] + '+00:00'
            
            try:
                last_lead_time = datetime.fromisoformat(last_lead_time_str)
                # Make sure we have timezone-aware datetime for comparison
                if last_lead_time.tzinfo is None:
                    # Assume UTC if no timezone
                    last_lead_time = last_lead_time.replace(tzinfo=timezone.utc)
                
                # Get current time as timezone-aware UTC
                current_time = datetime.now(timezone.utc)
                time_diff = current_time - last_lead_time
            except (ValueError, TypeError):
                # Fallback if datetime parsing fails
                time_diff = timedelta(hours=25)  # Outside normal time window
            time_since_minutes = int(time_diff.total_seconds() / 60)
            
            # Calculate message similarity with most recent lead
            last_message = most_recent_lead.metadata.get('message', '')
            message_similarity = await self.calculate_message_similarity(
                new_lead.message, last_message
            )
            
            self.logger.info(
                f"Duplicate analysis for contact: time_since={time_since_minutes}min, "
                f"similarity={message_similarity:.3f}, sequence={customer_sequence}, "
                f"thresholds: suspicious={self.duplicate_suspicious_threshold}@{self.duplicate_suspicious_window_minutes}min, "
                f"link={self.duplicate_message_threshold}@{self.duplicate_time_window_hours}hr"
            )
            
            # Apply business logic decision matrix
            
            # CASE 1: Very recent + very similar = likely accidental duplicate
            if (time_since_minutes < self.duplicate_suspicious_window_minutes and 
                message_similarity > self.duplicate_suspicious_threshold and
                self.flag_suspicious_duplicates):
                
                try:
                    parent_id = most_recent_lead.lead_id if isinstance(most_recent_lead.lead_id, UUID) else UUID(most_recent_lead.lead_id)
                    related_ids = []
                    for result in sorted_history:
                        try:
                            related_ids.append(result.lead_id if isinstance(result.lead_id, UUID) else UUID(result.lead_id))
                        except (ValueError, TypeError) as e:
                            self.logger.warning(f"Invalid UUID in related leads: {result.lead_id}, error: {e}")
                            continue
                except (ValueError, TypeError) as e:
                    self.logger.error(f"Invalid parent lead UUID: {most_recent_lead.lead_id}, error: {e}")
                    parent_id = None
                    related_ids = []
                
                return DuplicateAnalysisResult(
                    action="flag",
                    reason=f"Suspicious duplicate: {message_similarity:.2f} similarity within {time_since_minutes} minutes",
                    parent_lead_id=parent_id,
                    customer_sequence=customer_sequence,
                    time_since_last=time_since_minutes,
                    message_similarity=message_similarity,
                    related_leads=related_ids
                )
            
            # CASE 2: Same day + similar = possible follow-up, link it
            elif (time_since_minutes < (self.duplicate_time_window_hours * 60) and 
                  message_similarity > self.duplicate_message_threshold and
                  self.auto_link_related_leads):
                
                try:
                    parent_id = most_recent_lead.lead_id if isinstance(most_recent_lead.lead_id, UUID) else UUID(most_recent_lead.lead_id)
                    related_ids = []
                    for result in sorted_history:
                        try:
                            related_ids.append(result.lead_id if isinstance(result.lead_id, UUID) else UUID(result.lead_id))
                        except (ValueError, TypeError) as e:
                            self.logger.warning(f"Invalid UUID in related leads: {result.lead_id}, error: {e}")
                            continue
                except (ValueError, TypeError) as e:
                    self.logger.error(f"Invalid parent lead UUID: {most_recent_lead.lead_id}, error: {e}")
                    parent_id = None
                    related_ids = []
                
                return DuplicateAnalysisResult(
                    action="link",
                    reason=f"Related inquiry: {message_similarity:.2f} similarity within {time_since_minutes//60} hours",
                    parent_lead_id=parent_id,
                    customer_sequence=customer_sequence,
                    time_since_last=time_since_minutes,
                    message_similarity=message_similarity,
                    related_leads=related_ids
                )
            
            # CASE 3: Different message or older = new separate inquiry
            else:
                try:
                    related_ids = []
                    for result in sorted_history:
                        try:
                            related_ids.append(result.lead_id if isinstance(result.lead_id, UUID) else UUID(result.lead_id))
                        except (ValueError, TypeError) as e:
                            self.logger.warning(f"Invalid UUID in related leads: {result.lead_id}, error: {e}")
                            continue
                except Exception as e:
                    self.logger.error(f"Error processing related lead UUIDs: {e}")
                    related_ids = []
                
                return DuplicateAnalysisResult(
                    action="process",
                    reason=f"New inquiry from existing contact: {message_similarity:.2f} similarity, {time_since_minutes//60} hours since last",
                    customer_sequence=customer_sequence,
                    time_since_last=time_since_minutes,
                    message_similarity=message_similarity,
                    related_leads=related_ids
                )
                
        except Exception as e:
            self.logger.error(f"Error in duplicate analysis: {str(e)}")
            # Default to processing if analysis fails
            return DuplicateAnalysisResult(
                action="process",
                reason=f"Analysis failed, defaulting to process: {str(e)}",
                customer_sequence=len(contact_history) + 1 if contact_history else 1
            )


# Factory function
def create_duplicate_service() -> DuplicateServiceInterface:
    """Create and return duplicate service instance."""
    return SmartDuplicateAnalyzer()


# Singleton instance for dependency injection
_duplicate_service: Optional[DuplicateServiceInterface] = None


def get_duplicate_service() -> DuplicateServiceInterface:
    """Get or create duplicate service instance."""
    global _duplicate_service
    if _duplicate_service is None:
        _duplicate_service = create_duplicate_service()
    return _duplicate_service