"""Tests for Pydantic data models."""

import pytest
from datetime import datetime
from uuid import UUID
from pydantic import ValidationError

from src.models.lead import (
    AIAnalysis,
    ContactInfo,
    EnrichedLead,
    IntentCategory,
    LeadInput,
    LeadQuery,
    LeadSource,
    LeadStatus,
    LeadSummary,
    UrgencyLevel,
    VectorData
)
from src.models.airtable import (
    AirtableConfig,
    AirtableFieldMapping,
    AirtableRecord,
    SyncRecord,
    SyncStatus,
    SyncOperation
)


@pytest.mark.model
class TestContactInfo:
    """Test ContactInfo model validation."""
    
    def test_contact_info_valid(self):
        """Test valid contact info creation."""
        contact = ContactInfo(
            first_name="John",
            last_name="Doe",
            email="john@example.com",
            phone="+1234567890",
            company="Test Corp"
        )
        
        assert contact.first_name == "John"
        assert contact.last_name == "Doe"
        assert contact.email == "john@example.com"
        assert contact.phone == "+1234567890"
        assert contact.company == "Test Corp"
    
    def test_contact_info_optional_fields(self):
        """Test contact info with optional fields."""
        contact = ContactInfo()
        
        assert contact.first_name is None
        assert contact.last_name is None
        assert contact.email is None
        assert contact.phone is None
        assert contact.company is None
    
    def test_phone_validation_success(self):
        """Test successful phone number validation."""
        valid_phones = [
            "+1234567890",
            "123-456-7890",
            "(123) 456-7890",
            "1234567890"
        ]
        
        for phone in valid_phones:
            contact = ContactInfo(phone=phone)
            assert len(contact.phone) >= 10  # Should be cleaned
    
    def test_phone_validation_failure(self):
        """Test phone number validation failures."""
        with pytest.raises(ValidationError):
            ContactInfo(phone="123")  # Too short
    
    def test_email_validation(self):
        """Test email validation."""
        # Valid email
        contact = ContactInfo(email="test@example.com")
        assert contact.email == "test@example.com"
        
        # Invalid email
        with pytest.raises(ValidationError):
            ContactInfo(email="invalid-email")
    
    def test_full_name_property(self):
        """Test full_name property logic."""
        # Both names
        contact = ContactInfo(first_name="John", last_name="Doe")
        assert contact.full_name == "John Doe"
        
        # First name only
        contact = ContactInfo(first_name="John")
        assert contact.full_name == "John"
        
        # Last name only
        contact = ContactInfo(last_name="Doe")
        assert contact.full_name == "Doe"
        
        # No names
        contact = ContactInfo()
        assert contact.full_name is None
    
    def test_has_contact_method(self):
        """Test has_contact_method property."""
        # Has email
        contact = ContactInfo(email="test@example.com")
        assert contact.has_contact_method is True
        
        # Has phone
        contact = ContactInfo(phone="+1234567890")
        assert contact.has_contact_method is True
        
        # Has both
        contact = ContactInfo(email="test@example.com", phone="+1234567890")
        assert contact.has_contact_method is True
        
        # Has neither
        contact = ContactInfo()
        assert contact.has_contact_method is False


@pytest.mark.model
class TestLeadInput:
    """Test LeadInput model validation."""
    
    def test_lead_input_valid(self, sample_contact_info):
        """Test valid lead input creation."""
        lead_input = LeadInput(
            message="Test message",
            contact=sample_contact_info,
            source=LeadSource.WEB_FORM,
            source_url="https://example.com",
            custom_fields={"key": "value"}
        )
        
        assert lead_input.message == "Test message"
        assert lead_input.contact == sample_contact_info
        assert lead_input.source == LeadSource.WEB_FORM
        assert lead_input.source_url == "https://example.com"
        assert lead_input.custom_fields == {"key": "value"}
        assert isinstance(lead_input.received_at, datetime)
    
    def test_message_validation(self):
        """Test message field validation."""
        # Valid message
        lead_input = LeadInput(message="Valid message")
        assert lead_input.message == "Valid message"
        
        # Empty message
        with pytest.raises(ValidationError):
            LeadInput(message="")
        
        # Whitespace only
        with pytest.raises(ValidationError):
            LeadInput(message="   ")
        
        # Message too long
        with pytest.raises(ValidationError):
            LeadInput(message="x" * 2001)
    
    def test_default_values(self):
        """Test default values for optional fields."""
        lead_input = LeadInput(message="Test")
        
        assert isinstance(lead_input.contact, ContactInfo)
        assert lead_input.source == LeadSource.UNKNOWN
        assert lead_input.source_url is None
        assert lead_input.custom_fields == {}
        assert isinstance(lead_input.received_at, datetime)


@pytest.mark.model
class TestAIAnalysis:
    """Test AIAnalysis model validation."""
    
    def test_ai_analysis_valid(self):
        """Test valid AI analysis creation."""
        analysis = AIAnalysis(
            intent=IntentCategory.APPOINTMENT_REQUEST,
            intent_confidence=0.85,
            urgency=UrgencyLevel.HIGH,
            urgency_confidence=0.75,
            entities={"services": ["brake repair"]},
            quality_score=80,
            topics=["automotive", "repair"],
            summary="Customer needs brake repair",
            business_insights={"category": "repair"},
            model_used="mistral:latest",
            processing_time=1.5
        )
        
        assert analysis.intent == IntentCategory.APPOINTMENT_REQUEST
        assert analysis.intent_confidence == 0.85
        assert analysis.urgency == UrgencyLevel.HIGH
        assert analysis.quality_score == 80
        assert isinstance(analysis.analyzed_at, datetime)
    
    def test_confidence_validation(self):
        """Test confidence score validation (0-1 range)."""
        # Valid confidence
        analysis = AIAnalysis(intent_confidence=0.5, urgency_confidence=0.8)
        assert analysis.intent_confidence == 0.5
        
        # Invalid confidence (too high)
        with pytest.raises(ValidationError):
            AIAnalysis(intent_confidence=1.5)
        
        # Invalid confidence (negative)
        with pytest.raises(ValidationError):
            AIAnalysis(urgency_confidence=-0.1)
    
    def test_quality_score_validation(self):
        """Test quality score validation (0-100 range)."""
        # Valid scores
        for score in [0, 50, 100]:
            analysis = AIAnalysis(quality_score=score)
            assert analysis.quality_score == score
        
        # Invalid scores
        with pytest.raises(ValidationError):
            AIAnalysis(quality_score=-1)
        
        with pytest.raises(ValidationError):
            AIAnalysis(quality_score=101)


@pytest.mark.model
class TestEnrichedLead:
    """Test EnrichedLead model validation and methods."""
    
    def test_enriched_lead_creation(self, sample_lead_input):
        """Test enriched lead creation from lead input."""
        enriched = EnrichedLead(**sample_lead_input.dict())
        
        assert enriched.message == sample_lead_input.message
        assert enriched.contact == sample_lead_input.contact
        assert enriched.status == LeadStatus.RAW
        assert isinstance(enriched.id, UUID)
    
    def test_mark_processing(self, sample_enriched_lead):
        """Test marking lead as processing."""
        lead = sample_enriched_lead
        lead.mark_processing()
        
        assert lead.status == LeadStatus.PROCESSING
        assert lead.processed_at is not None
    
    def test_mark_enriched(self, sample_enriched_lead, sample_ai_analysis):
        """Test marking lead as enriched."""
        lead = sample_enriched_lead
        lead.mark_enriched(sample_ai_analysis)
        
        assert lead.status == LeadStatus.ENRICHED
        assert lead.ai_analysis == sample_ai_analysis
        assert lead.enriched_at is not None
    
    def test_mark_synced(self, sample_enriched_lead):
        """Test marking lead as synced."""
        lead = sample_enriched_lead
        lead.mark_synced("airtable", "rec123")
        
        assert lead.status == LeadStatus.SYNCED
        assert lead.external_ids["airtable"] == "rec123"
        assert lead.synced_at is not None
    
    def test_mark_failed(self, sample_enriched_lead):
        """Test marking lead as failed."""
        lead = sample_enriched_lead
        error_msg = "Processing failed"
        lead.mark_failed(error_msg)
        
        assert lead.status == LeadStatus.FAILED
        assert error_msg in lead.processing_errors
        assert lead.retry_count == 1
    
    def test_properties(self, sample_enriched_lead):
        """Test computed properties."""
        lead = sample_enriched_lead
        
        # has_ai_analysis
        assert lead.has_ai_analysis is True
        
        # has_vector_data
        assert lead.has_vector_data is True
        
        # is_high_quality (quality_score = 82)
        assert lead.is_high_quality is True
        
        # is_urgent (urgency = HIGH)
        assert lead.is_urgent is True


@pytest.mark.model
class TestLeadQuery:
    """Test LeadQuery model validation."""
    
    def test_lead_query_defaults(self):
        """Test default values."""
        query = LeadQuery()
        
        assert query.limit == 10
        assert query.offset == 0
        assert query.sort_by == "received_at"
        assert query.sort_order == "desc"
    
    def test_lead_query_validation(self):
        """Test field validation."""
        # Valid query
        query = LeadQuery(
            limit=50,
            offset=100,
            status=LeadStatus.ENRICHED,
            min_quality_score=70
        )
        
        assert query.limit == 50
        assert query.offset == 100
        assert query.status == LeadStatus.ENRICHED
        assert query.min_quality_score == 70
        
        # Invalid limit (too high)
        with pytest.raises(ValidationError):
            LeadQuery(limit=101)
        
        # Invalid quality score
        with pytest.raises(ValidationError):
            LeadQuery(min_quality_score=-1)


@pytest.mark.model
class TestVectorData:
    """Test VectorData model validation."""
    
    def test_vector_data_valid(self):
        """Test valid vector data creation."""
        vector_data = VectorData(
            embedding=[0.1, 0.2, 0.3],
            embedding_model="test-model",
            text_hash="abc123"
        )
        
        assert vector_data.embedding == [0.1, 0.2, 0.3]
        assert vector_data.embedding_model == "test-model"
        assert vector_data.text_hash == "abc123"
        assert isinstance(vector_data.created_at, datetime)
    
    def test_embedding_validation(self):
        """Test embedding validation."""
        # Empty embedding
        with pytest.raises(ValidationError):
            VectorData(
                embedding=[],
                embedding_model="test",
                text_hash="abc"
            )


@pytest.mark.model
class TestAirtableModels:
    """Test Airtable integration models."""
    
    def test_airtable_config_validation(self):
        """Test AirtableConfig validation."""
        config = AirtableConfig(
            base_id="appXXXXXXXXXXXXXX",
            table_name="Leads",
            api_key="patXXXXXXXXXXXXXX"
        )
        
        assert config.base_id.startswith("app")
        assert config.api_key.startswith("pat")
        
        # Invalid base_id
        with pytest.raises(ValidationError):
            AirtableConfig(
                base_id="invalid",
                table_name="Leads",
                api_key="patXXX"
            )
        
        # Invalid API key
        with pytest.raises(ValidationError):
            AirtableConfig(
                base_id="appXXX",
                table_name="Leads",
                api_key="invalid"
            )
    
    def test_airtable_record_creation(self, sample_enriched_lead):
        """Test AirtableRecord creation from EnrichedLead."""
        field_mapping = AirtableFieldMapping()
        record = AirtableRecord.from_enriched_lead(
            sample_enriched_lead,
            field_mapping
        )
        
        assert record.lead_id == sample_enriched_lead.id
        assert record.fields[field_mapping.message_field] == sample_enriched_lead.message
        assert record.fields[field_mapping.email_field] == str(sample_enriched_lead.contact.email)
    
    def test_sync_record_lifecycle(self):
        """Test SyncRecord status lifecycle."""
        from uuid import uuid4
        
        sync_record = SyncRecord(
            lead_id=uuid4(),
            operation=SyncOperation.CREATE,
            base_id="appXXX",
            table_name="Leads"
        )
        
        # Initial state
        assert sync_record.status == SyncStatus.PENDING
        assert sync_record.can_retry() is False
        
        # Mark started
        sync_record.mark_started()
        assert sync_record.status == SyncStatus.IN_PROGRESS
        assert sync_record.started_at is not None
        
        # Mark failed
        sync_record.mark_failed("Test error")
        assert sync_record.status == SyncStatus.FAILED
        assert sync_record.error_message == "Test error"
        assert sync_record.retry_count == 1
        assert sync_record.can_retry() is True
        
        # Mark success
        sync_record.mark_success("rec123")
        assert sync_record.status == SyncStatus.SUCCESS
        assert sync_record.airtable_record_id == "rec123"
        assert sync_record.is_complete is True


@pytest.mark.model
class TestLeadSummary:
    """Test LeadSummary model."""
    
    def test_lead_summary_from_enriched(self, sample_enriched_lead):
        """Test creating LeadSummary from EnrichedLead."""
        summary = LeadSummary.from_enriched_lead(sample_enriched_lead)
        
        assert summary.id == sample_enriched_lead.id
        assert summary.contact_name == sample_enriched_lead.contact.full_name
        assert summary.contact_email == sample_enriched_lead.contact.email
        assert summary.source == sample_enriched_lead.source
        assert summary.status == sample_enriched_lead.status
        assert summary.intent == sample_enriched_lead.ai_analysis.intent
        assert summary.quality_score == sample_enriched_lead.ai_analysis.quality_score
    
    def test_message_truncation(self, sample_lead_input):
        """Test message truncation in summary."""
        # Long message
        long_message = "x" * 250
        lead_input = LeadInput(message=long_message)
        enriched = EnrichedLead(**lead_input.dict())
        
        summary = LeadSummary.from_enriched_lead(enriched)
        assert len(summary.message) <= 203  # 200 + "..."
        assert summary.message.endswith("...")


if __name__ == "__main__":
    pytest.main([__file__])