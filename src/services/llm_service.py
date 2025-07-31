"""LLM service for lead analysis using Ollama."""

import asyncio
import json
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import httpx
from pydantic import BaseModel, Field

from ..config.settings import settings
from ..models.lead import (
    AIAnalysis, 
    EnrichedLead, 
    IntentCategory, 
    LeadInput, 
    UrgencyLevel
)


class PromptTemplate(BaseModel):
    """Template for LLM prompts."""
    
    system_prompt: str
    user_prompt: str
    
    def format(self, **kwargs) -> Tuple[str, str]:
        """Format the prompt with provided variables."""
        return (
            self.system_prompt.format(**kwargs),
            self.user_prompt.format(**kwargs)
        )


class LLMResponse(BaseModel):
    """Structured response from LLM."""
    
    content: str
    model: str
    total_duration: Optional[int] = None
    load_duration: Optional[int] = None
    prompt_eval_count: Optional[int] = None
    prompt_eval_duration: Optional[int] = None
    eval_count: Optional[int] = None
    eval_duration: Optional[int] = None


class LLMServiceError(Exception):
    """Base exception for LLM service errors."""
    pass


class LLMConnectionError(LLMServiceError):
    """Error connecting to LLM service."""
    pass


class LLMTimeoutError(LLMServiceError):
    """LLM request timeout error."""
    pass


class LLMServiceInterface(ABC):
    """Abstract interface for LLM services."""
    
    @abstractmethod
    async def analyze_lead(self, lead: LeadInput) -> AIAnalysis:
        """Analyze lead content and return AI analysis."""
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Check if LLM service is available."""
        pass
    
    @abstractmethod
    async def get_available_models(self) -> List[str]:
        """Get list of available models."""
        pass


class OllamaService(LLMServiceInterface):
    """Ollama LLM service implementation."""
    
    def __init__(self):
        self.base_url = settings.ollama_base_url.rstrip("/")
        self.model = settings.ollama_model
        self.timeout = settings.ollama_timeout
        self.logger = logging.getLogger(__name__)
        
        # Initialize HTTP client
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(self.timeout),
            limits=httpx.Limits(max_connections=10, max_keepalive_connections=5)
        )
        
        # Load prompt templates
        self.prompt_templates = self._load_prompt_templates()
    
    def _load_prompt_templates(self) -> Dict[str, PromptTemplate]:
        """Load prompt templates for different business types."""
        templates = {
            "general": PromptTemplate(
                system_prompt="""You are an AI assistant specialized in analyzing customer inquiries for small businesses. 
Your task is to analyze the lead content and extract key information in a structured format.

Respond ONLY with valid JSON in this exact format:
{{
    "intent": "inquiry|appointment_request|quote_request|support|complaint|general",
    "intent_confidence": 0.85,
    "urgency": "low|medium|high|urgent", 
    "urgency_confidence": 0.75,
    "entities": {{
        "services": ["service1", "service2"],
        "locations": ["location1"],
        "dates": ["date1"],
        "contact_preferences": ["email", "phone"]
    }},
    "quality_score": 75,
    "topics": ["topic1", "topic2"],
    "summary": "Brief summary of the inquiry",
    "business_insights": {{
        "customer_type": "new|returning",
        "purchase_intent": "high|medium|low"
    }}
}}""",
                user_prompt="""Analyze this customer inquiry:

Message: {message}
Contact Info: {contact_info}
Source: {source}

Extract the intent, urgency, entities, and provide a quality score (0-100) based on lead potential."""
            ),
            
            "automotive": PromptTemplate(
                system_prompt="""You are an AI assistant specialized in analyzing customer inquiries for automotive service businesses (mechanics, auto repair shops, car dealerships).

Focus on automotive-specific entities like:
- Vehicle information (make, model, year, mileage)
- Service types (oil change, brake repair, engine diagnostics, etc.)
- Symptoms or issues described
- Urgency indicators (car won't start, safety issues, etc.)

Respond ONLY with valid JSON in this exact format:
{{
    "intent": "inquiry|appointment_request|quote_request|support|complaint|general",
    "intent_confidence": 0.85,
    "urgency": "low|medium|high|urgent",
    "urgency_confidence": 0.75,
    "entities": {{
        "vehicle_info": ["2018 Honda Civic"],
        "services": ["brake repair", "oil change"],
        "symptoms": ["grinding noise", "low oil pressure"],
        "locations": ["downtown shop"],
        "dates": ["next week"],
        "contact_preferences": ["phone"]
    }},
    "quality_score": 75,
    "topics": ["brake_repair", "vehicle_maintenance"],
    "summary": "Brief summary focusing on automotive needs",
    "business_insights": {{
        "service_category": "maintenance|repair|emergency|inspection",
        "customer_type": "new|returning",
        "vehicle_age": "new|used|older"
    }}
}}""",
                user_prompt="""Analyze this automotive service inquiry:

Message: {message}
Contact Info: {contact_info}
Source: {source}

Focus on vehicle details, service needs, and urgency indicators."""
            ),
            
            "medspa": PromptTemplate(
                system_prompt="""You are an AI assistant specialized in analyzing customer inquiries for medical spa and aesthetic treatment businesses.

Focus on medspa-specific entities like:
- Treatment types (Botox, fillers, laser treatments, facials, etc.)
- Areas of concern (wrinkles, acne, skin texture, body contouring)
- Previous treatments or experience
- Consultation requests
- Special events or timing needs

Respond ONLY with valid JSON in this exact format:
{{
    "intent": "inquiry|appointment_request|quote_request|support|complaint|general",
    "intent_confidence": 0.85,
    "urgency": "low|medium|high|urgent",
    "urgency_confidence": 0.75,
    "entities": {{
        "treatments": ["Botox", "facial"],
        "concerns": ["wrinkles", "acne scars"],
        "body_areas": ["face", "forehead"],
        "timing": ["before wedding", "next month"],
        "experience_level": ["first time", "returning client"],
        "contact_preferences": ["email", "text"]
    }},
    "quality_score": 75,
    "topics": ["anti_aging", "skin_care"],
    "summary": "Brief summary focusing on aesthetic goals",
    "business_insights": {{
        "treatment_category": "facial|body|anti_aging|acne|consultation",
        "customer_type": "new|returning",
        "budget_indicator": "high|medium|low|unspecified"
    }}
}}""",
                user_prompt="""Analyze this medical spa inquiry:

Message: {message}
Contact Info: {contact_info}
Source: {source}

Focus on treatment interests, aesthetic concerns, and consultation needs."""
            ),
            
            "consulting": PromptTemplate(
                system_prompt="""You are an AI assistant specialized in analyzing inquiries for professional consulting businesses.

Focus on consulting-specific entities like:
- Service areas (strategy, operations, technology, HR, finance, etc.)
- Project scope indicators (small business, enterprise, specific departments)
- Timeline requirements
- Budget indicators
- Current challenges or pain points

Respond ONLY with valid JSON in this exact format:
{{
    "intent": "inquiry|appointment_request|quote_request|support|complaint|general",
    "intent_confidence": 0.85,
    "urgency": "low|medium|high|urgent",
    "urgency_confidence": 0.75,
    "entities": {{
        "services": ["strategy consulting", "process improvement"],
        "industry": ["healthcare", "manufacturing"],
        "company_size": ["small business", "enterprise"],
        "timeline": ["Q1", "next month"],
        "budget_range": ["under 10k", "50k+"],
        "contact_preferences": ["email", "phone"]
    }},
    "quality_score": 75,
    "topics": ["business_strategy", "operations"],
    "summary": "Brief summary focusing on consulting needs",
    "business_insights": {{
        "service_category": "strategy|operations|technology|hr|finance|general",
        "project_scope": "small|medium|enterprise",
        "decision_maker": "likely|possible|unlikely"
    }}
}}""",
                user_prompt="""Analyze this consulting inquiry:

Message: {message}
Contact Info: {contact_info}
Source: {source}

Focus on consulting needs, project scope, and decision-making authority."""
            )
        }
        
        return templates
    
    async def analyze_lead(self, lead: LeadInput) -> AIAnalysis:
        """Analyze lead content using Ollama."""
        try:
            # Select appropriate prompt template
            business_type = settings.business_type
            template = self.prompt_templates.get(business_type, self.prompt_templates["general"])
            
            # Format contact info for prompt
            contact_info = ""
            if lead.contact.full_name:
                contact_info += f"Name: {lead.contact.full_name}\n"
            if lead.contact.email:
                contact_info += f"Email: {lead.contact.email}\n"
            if lead.contact.phone:
                contact_info += f"Phone: {lead.contact.phone}\n"
            if lead.contact.company:
                contact_info += f"Company: {lead.contact.company}\n"
            
            # Format prompts
            system_prompt, user_prompt = template.format(
                message=lead.message,
                contact_info=contact_info.strip(),
                source=lead.source.value
            )
            
            # Make request to Ollama
            start_time = datetime.utcnow()
            response = await self._make_ollama_request(system_prompt, user_prompt)
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            
            # Parse JSON response
            try:
                analysis_data = json.loads(response.content)
            except json.JSONDecodeError as e:
                self.logger.error(f"Failed to parse LLM JSON response: {e}")
                self.logger.debug(f"Raw response: {response.content}")
                return self._create_fallback_analysis(lead, processing_time, response.model)
            
            # Create AIAnalysis from parsed data
            ai_analysis = self._parse_analysis_response(
                analysis_data, 
                processing_time, 
                response.model
            )
            
            self.logger.info(
                f"Successfully analyzed lead {lead.message[:50]}... "
                f"(intent: {ai_analysis.intent}, quality: {ai_analysis.quality_score})"
            )
            
            return ai_analysis
            
        except Exception as e:
            self.logger.error(f"Error analyzing lead: {str(e)}")
            # Return fallback analysis rather than failing completely
            return self._create_fallback_analysis(lead, 0.0, self.model, str(e))
    
    async def _make_ollama_request(self, system_prompt: str, user_prompt: str) -> LLMResponse:
        """Make request to Ollama API."""
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "stream": False,
            "options": {
                "temperature": 0.1,  # Low temperature for consistent structured output
                "top_p": 0.9,
                "num_ctx": 4096
            }
        }
        
        try:
            response = await self.client.post(
                f"{self.base_url}/api/chat",
                json=payload
            )
            response.raise_for_status()
            
            data = response.json()
            return LLMResponse(
                content=data["message"]["content"],
                model=data.get("model", self.model),
                total_duration=data.get("total_duration"),
                load_duration=data.get("load_duration"),
                prompt_eval_count=data.get("prompt_eval_count"),
                prompt_eval_duration=data.get("prompt_eval_duration"),
                eval_count=data.get("eval_count"),
                eval_duration=data.get("eval_duration")
            )
            
        except httpx.TimeoutException:
            raise LLMTimeoutError(f"Request to Ollama timed out after {self.timeout}s")
        except httpx.HTTPStatusError as e:
            raise LLMConnectionError(f"HTTP error from Ollama: {e.response.status_code}")
        except httpx.RequestError as e:
            raise LLMConnectionError(f"Request error to Ollama: {str(e)}")
    
    def _parse_analysis_response(self, data: Dict, processing_time: float, model: str) -> AIAnalysis:
        """Parse LLM response data into AIAnalysis object."""
        try:
            # Map string values to enums with fallbacks
            intent = IntentCategory(data.get("intent", "general"))
        except ValueError:
            intent = IntentCategory.GENERAL
        
        try:
            urgency = UrgencyLevel(data.get("urgency", "medium"))
        except ValueError:
            urgency = UrgencyLevel.MEDIUM
        
        return AIAnalysis(
            intent=intent,
            intent_confidence=max(0.0, min(1.0, data.get("intent_confidence", 0.5))),
            urgency=urgency,
            urgency_confidence=max(0.0, min(1.0, data.get("urgency_confidence", 0.5))),
            entities=data.get("entities", {}),
            quality_score=max(0, min(100, data.get("quality_score", 50))),
            topics=data.get("topics", []),
            summary=data.get("summary"),
            business_insights=data.get("business_insights", {}),
            model_used=model,
            processing_time=processing_time
        )
    
    def _create_fallback_analysis(
        self, 
        lead: LeadInput, 
        processing_time: float, 
        model: str,
        error: Optional[str] = None
    ) -> AIAnalysis:
        """Create basic fallback analysis when LLM fails."""
        self.logger.warning(f"Creating fallback analysis for lead. Error: {error}")
        
        # Basic heuristic analysis
        quality_score = 30  # Default low quality for fallback
        urgency = UrgencyLevel.MEDIUM
        intent = IntentCategory.GENERAL
        
        # Simple keyword-based urgency detection
        urgent_keywords = ["urgent", "emergency", "asap", "immediately", "broken", "won't start"]
        if any(keyword in lead.message.lower() for keyword in urgent_keywords):
            urgency = UrgencyLevel.HIGH
            quality_score += 20
        
        # Simple keyword-based intent detection
        appointment_keywords = ["appointment", "schedule", "book", "meeting"]
        if any(keyword in lead.message.lower() for keyword in appointment_keywords):
            intent = IntentCategory.APPOINTMENT_REQUEST
            quality_score += 15
        
        # Quality boost if contact info is provided
        if lead.contact.has_contact_method:
            quality_score += 25
        
        return AIAnalysis(
            intent=intent,
            intent_confidence=0.3,  # Low confidence for fallback
            urgency=urgency,
            urgency_confidence=0.3,
            entities={"fallback": ["true"]},
            quality_score=min(100, quality_score),
            topics=["fallback_analysis"],
            summary="Fallback analysis - LLM processing failed",
            business_insights={"analysis_type": "fallback"},
            model_used=f"{model}_fallback",
            processing_time=processing_time
        )
    
    async def health_check(self) -> bool:
        """Check if Ollama service is available."""
        try:
            response = await self.client.get(f"{self.base_url}/api/tags")
            return response.status_code == 200
        except Exception as e:
            self.logger.error(f"Ollama health check failed: {str(e)}")
            return False
    
    async def get_available_models(self) -> List[str]:
        """Get list of available models from Ollama."""
        try:
            response = await self.client.get(f"{self.base_url}/api/tags")
            response.raise_for_status()
            
            data = response.json()
            return [model["name"] for model in data.get("models", [])]
        except Exception as e:
            self.logger.error(f"Failed to get available models: {str(e)}")
            return []
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.client.aclose()


# Factory function for creating LLM service
def create_llm_service() -> LLMServiceInterface:
    """Create and return appropriate LLM service instance."""
    return OllamaService()


# Singleton instance for dependency injection
_llm_service: Optional[LLMServiceInterface] = None


async def get_llm_service() -> LLMServiceInterface:
    """Get or create LLM service instance."""
    global _llm_service
    if _llm_service is None:
        _llm_service = create_llm_service()
    return _llm_service