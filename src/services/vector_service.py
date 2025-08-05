"""Vector database service for lead similarity and deduplication using ChromaDB."""

import hashlib
import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple
from uuid import UUID

import chromadb
from chromadb.config import Settings as ChromaSettings
from sentence_transformers import SentenceTransformer

from ..config.settings import settings
from ..models.lead import EnrichedLead, LeadInput, VectorData


class VectorServiceError(Exception):
    """Base exception for vector service errors."""
    pass


class EmbeddingError(VectorServiceError):
    """Error generating embeddings."""
    pass


class ChromaDBError(VectorServiceError):
    """Error with ChromaDB operations."""
    pass


class SimilarityResult:
    """Result from similarity search."""
    
    def __init__(self, lead_id: UUID, similarity_score: float, metadata: Dict):
        self.lead_id = lead_id
        self.similarity_score = similarity_score
        self.metadata = metadata
    
    def __repr__(self):
        return f"SimilarityResult(lead_id={self.lead_id}, score={self.similarity_score:.3f})"


class VectorServiceInterface(ABC):
    """Abstract interface for vector database services."""
    
    @abstractmethod
    async def add_lead(self, lead: EnrichedLead) -> VectorData:
        """Add lead to vector database with embedding."""
        pass
    
    @abstractmethod
    async def find_similar_leads(
        self, 
        lead: LeadInput, 
        threshold: float = None,
        limit: int = None
    ) -> List[SimilarityResult]:
        """Find similar leads in the database."""
        pass
    
    @abstractmethod
    async def update_lead(self, lead: EnrichedLead) -> VectorData:
        """Update existing lead in vector database."""
        pass
    
    @abstractmethod
    async def remove_lead(self, lead_id: UUID) -> bool:
        """Remove lead from vector database."""
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Check if vector service is available."""
        pass


class ChromaVectorService(VectorServiceInterface):
    """ChromaDB implementation of vector service."""
    
    def __init__(self):
        self.persist_directory = settings.chroma_persist_directory
        self.collection_name = settings.chroma_collection_name
        self.similarity_threshold = settings.lead_similarity_threshold
        self.max_similar_leads = settings.max_similar_leads
        self.logger = logging.getLogger(__name__)
        
        # Initialize embedding model
        self.embedding_model_name = "all-MiniLM-L6-v2"
        self.embedding_model = None
        
        # Initialize ChromaDB client
        self.client = None
        self.collection = None
        
        # Initialize components
        self._initialize_client()
        self._initialize_embedding_model()
        self._initialize_collection()
    
    def _initialize_client(self):
        """Initialize ChromaDB client."""
        try:
            self.client = chromadb.PersistentClient(
                path=self.persist_directory,
                settings=ChromaSettings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
            self.logger.info(f"ChromaDB client initialized with persist directory: {self.persist_directory}")
        except Exception as e:
            self.logger.error(f"Failed to initialize ChromaDB client: {str(e)}")
            raise ChromaDBError(f"ChromaDB initialization failed: {str(e)}")
    
    def _initialize_embedding_model(self):
        """Initialize sentence transformer model."""
        try:
            self.embedding_model = SentenceTransformer(self.embedding_model_name)
            self.logger.info(f"Embedding model '{self.embedding_model_name}' loaded successfully")
        except Exception as e:
            self.logger.error(f"Failed to load embedding model: {str(e)}")
            raise EmbeddingError(f"Embedding model initialization failed: {str(e)}")
    
    def _initialize_collection(self):
        """Initialize or get ChromaDB collection."""
        try:
            # Try to get existing collection
            try:
                self.collection = self.client.get_collection(name=self.collection_name)
                self.logger.info(f"Using existing collection: {self.collection_name}")
            except Exception:
                # Create new collection if it doesn't exist
                self.collection = self.client.create_collection(
                    name=self.collection_name,
                    metadata={
                        "description": "Lead embeddings for similarity search and deduplication",
                        "embedding_model": self.embedding_model_name,
                        "created_at": str(settings)
                    }
                )
                self.logger.info(f"Created new collection: {self.collection_name}")
                
        except Exception as e:
            self.logger.error(f"Failed to initialize collection: {str(e)}")
            raise ChromaDBError(f"Collection initialization failed: {str(e)}")
    
    def _generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text using sentence transformer."""
        try:
            if not self.embedding_model:
                raise EmbeddingError("Embedding model not initialized")
            
            # Normalize text
            normalized_text = text.strip().lower()
            if not normalized_text:
                raise EmbeddingError("Empty text provided for embedding")
            
            # Generate embedding
            embedding = self.embedding_model.encode(normalized_text, convert_to_tensor=False)
            return embedding.tolist()
            
        except Exception as e:
            self.logger.error(f"Failed to generate embedding: {str(e)}")
            raise EmbeddingError(f"Embedding generation failed: {str(e)}")
    
    def _create_text_hash(self, text: str) -> str:
        """Create hash of text for deduplication."""
        normalized_text = text.strip().lower()
        return hashlib.sha256(normalized_text.encode()).hexdigest()
    
    def _prepare_lead_text(self, lead: LeadInput) -> str:
        """Prepare lead text for embedding generation."""
        text_parts = [lead.message]
        
        # Add contact information if available
        if lead.contact.full_name:
            text_parts.append(f"Contact: {lead.contact.full_name}")
        
        if lead.contact.company:
            text_parts.append(f"Company: {lead.contact.company}")
        
        # Add custom fields
        for key, value in lead.custom_fields.items():
            if value:
                text_parts.append(f"{key}: {value}")
        
        return " | ".join(text_parts)
    
    async def add_lead(self, lead: EnrichedLead) -> VectorData:
        """Add lead to vector database with embedding."""
        try:
            # Prepare text for embedding
            lead_text = self._prepare_lead_text(lead)
            text_hash = self._create_text_hash(lead_text)
            
            # Generate embedding
            embedding = self._generate_embedding(lead_text)
            
            # Prepare metadata
            metadata = {
                "lead_id": str(lead.id),
                "message": lead.message[:500],  # Truncated for storage
                "source": lead.source.value,
                "status": lead.status.value,
                "received_at": lead.received_at.isoformat(),
                "text_hash": text_hash
            }
            
            # Add contact info to metadata if available
            if lead.contact.full_name:
                metadata["contact_name"] = lead.contact.full_name
            if lead.contact.email:
                metadata["contact_email"] = str(lead.contact.email)
            if lead.contact.company:
                metadata["company"] = lead.contact.company
            
            # Add AI analysis to metadata if available
            if lead.ai_analysis:
                metadata.update({
                    "intent": lead.ai_analysis.intent.value,
                    "urgency": lead.ai_analysis.urgency.value,
                    "quality_score": lead.ai_analysis.quality_score
                })
            
            # Add to ChromaDB collection
            self.collection.add(
                embeddings=[embedding],
                documents=[lead_text],
                metadatas=[metadata],
                ids=[str(lead.id)]
            )
            
            # Create VectorData object
            vector_data = VectorData(
                embedding=embedding,
                embedding_model=self.embedding_model_name,
                text_hash=text_hash
            )
            
            self.logger.info(f"Added lead {lead.id} to vector database")
            return vector_data
            
        except Exception as e:
            self.logger.error(f"Failed to add lead to vector database: {str(e)}")
            raise ChromaDBError(f"Failed to add lead: {str(e)}")
    
    async def find_similar_leads(
        self, 
        lead: LeadInput, 
        threshold: float = None,
        limit: int = None
    ) -> List[SimilarityResult]:
        """Find similar leads in the database."""
        try:
            threshold = threshold or self.similarity_threshold
            limit = limit or self.max_similar_leads
            
            # Prepare text and generate embedding
            lead_text = self._prepare_lead_text(lead)
            query_embedding = self._generate_embedding(lead_text)
            
            # Query ChromaDB
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=limit,
                include=["distances", "metadatas", "documents"]
            )
            
            # Process results
            similar_leads = []
            if results["ids"] and results["ids"][0]:  # Check if results exist
                for i, (lead_id, distance, metadata) in enumerate(
                    zip(results["ids"][0], results["distances"][0], results["metadatas"][0])
                ):
                    # Convert distance to similarity score (0-1, higher is more similar)
                    similarity_score = 1.0 - distance
                    
                    # Filter by threshold
                    if similarity_score >= threshold:
                        similar_leads.append(
                            SimilarityResult(
                                lead_id=UUID(lead_id),
                                similarity_score=similarity_score,
                                metadata=metadata
                            )
                        )
            
            # Sort by similarity score descending
            similar_leads.sort(key=lambda x: x.similarity_score, reverse=True)
            
            self.logger.info(
                f"Found {len(similar_leads)} similar leads "
                f"(threshold: {threshold:.2f}, total queried: {limit})"
            )
            
            return similar_leads
            
        except Exception as e:
            self.logger.error(f"Failed to find similar leads: {str(e)}")
            raise ChromaDBError(f"Similarity search failed: {str(e)}")
    
    async def update_lead(self, lead: EnrichedLead) -> VectorData:
        """Update existing lead in vector database."""
        try:
            # Remove existing entry
            await self.remove_lead(lead.id)
            
            # Add updated entry
            return await self.add_lead(lead)
            
        except Exception as e:
            self.logger.error(f"Failed to update lead in vector database: {str(e)}")
            raise ChromaDBError(f"Failed to update lead: {str(e)}")
    
    async def remove_lead(self, lead_id: UUID) -> bool:
        """Remove lead from vector database."""
        try:
            # Check if lead exists
            existing = self.collection.get(ids=[str(lead_id)])
            if not existing["ids"]:
                self.logger.warning(f"Lead {lead_id} not found in vector database")
                return False
            
            # Delete from collection
            self.collection.delete(ids=[str(lead_id)])
            
            self.logger.info(f"Removed lead {lead_id} from vector database")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to remove lead from vector database: {str(e)}")
            raise ChromaDBError(f"Failed to remove lead: {str(e)}")
    
    async def health_check(self) -> bool:
        """Check if vector service is available."""
        try:
            # Test basic operations
            if not self.client or not self.collection or not self.embedding_model:
                return False
            
            # Test embedding generation
            test_embedding = self._generate_embedding("test message")
            if not test_embedding or len(test_embedding) == 0:
                return False
            
            # Test ChromaDB query (empty query should work)
            self.collection.query(
                query_embeddings=[test_embedding],
                n_results=1
            )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Vector service health check failed: {str(e)}")
            return False
    
    def get_collection_stats(self) -> Dict:
        """Get statistics about the collection."""
        try:
            count = self.collection.count()
            
            return {
                "collection_name": self.collection_name,
                "total_leads": count,
                "embedding_model": self.embedding_model_name,
                "similarity_threshold": self.similarity_threshold,
                "max_similar_leads": self.max_similar_leads,
                "persist_directory": self.persist_directory
            }
        except Exception as e:
            self.logger.error(f"Failed to get collection stats: {str(e)}")
            return {"error": str(e)}
    
    async def find_potential_duplicates(
        self, 
        threshold: float = 0.95
    ) -> List[Tuple[UUID, UUID, float]]:
        """Find potential duplicate leads in the database."""
        try:
            # Get all leads from collection
            all_leads = self.collection.get(include=["embeddings", "metadatas"])
            
            if not all_leads["ids"]:
                return []
            
            duplicates = []
            embeddings = all_leads["embeddings"]
            ids = all_leads["ids"]
            
            # Compare all pairs
            for i in range(len(ids)):
                for j in range(i + 1, len(ids)):
                    # Calculate cosine similarity between embeddings
                    embedding1 = embeddings[i]
                    embedding2 = embeddings[j]
                    
                    # Simple dot product similarity (embeddings are normalized)
                    similarity = sum(a * b for a, b in zip(embedding1, embedding2))
                    
                    if similarity >= threshold:
                        duplicates.append((
                            UUID(ids[i]),
                            UUID(ids[j]),
                            similarity
                        ))
            
            # Sort by similarity descending
            duplicates.sort(key=lambda x: x[2], reverse=True)
            
            self.logger.info(f"Found {len(duplicates)} potential duplicates (threshold: {threshold:.2f})")
            return duplicates
            
        except Exception as e:
            self.logger.error(f"Failed to find potential duplicates: {str(e)}")
            raise ChromaDBError(f"Duplicate detection failed: {str(e)}")


# Factory function for creating vector service
def create_vector_service() -> VectorServiceInterface:
    """Create and return appropriate vector service instance."""
    return ChromaVectorService()


# Singleton instance for dependency injection
_vector_service: Optional[VectorServiceInterface] = None


def get_vector_service() -> VectorServiceInterface:
    """Get or create vector service instance."""
    global _vector_service
    if _vector_service is None:
        _vector_service = create_vector_service()
    return _vector_service