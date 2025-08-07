"""Tests for smart duplicate detection functionality."""

import pytest
from datetime import datetime, timedelta, timezone
from typing import List
from uuid import uuid4

from src.models.lead import ContactInfo, DuplicateStatus, EnrichedLead, LeadInput, LeadSource
from src.services.duplicate_service import DuplicateAnalysisResult, SmartDuplicateAnalyzer
from src.services.vector_service import SimilarityResult


class TestSmartDuplicateAnalyzer:
    """Test smart duplicate analyzer functionality."""
    
    @pytest.fixture
    def analyzer(self):
        """Create a duplicate analyzer instance."""
        return SmartDuplicateAnalyzer()
    
    @pytest.fixture
    def contact_john(self):
        """Sample contact info for John Doe."""
        return ContactInfo(
            first_name="John",
            last_name="Doe", 
            email="john.doe@email.com",
            phone="5551234567"
        )
    
    @pytest.fixture
    def contact_jane(self):
        """Sample contact info for Jane Smith."""
        return ContactInfo(
            first_name="Jane",
            last_name="Smith",
            email="jane.smith@email.com", 
            phone="5559876543"
        )
    
    @pytest.fixture
    def oil_change_message(self):
        """Oil change service message."""
        return "My 2019 Honda Civic needs an oil change. When can I schedule?"
    
    @pytest.fixture
    def brake_repair_message(self):
        """Brake repair service message."""
        return "I'm hearing grinding noises when I brake. Need inspection ASAP."
    
    @pytest.fixture
    def similar_oil_change_message(self):
        """Very similar oil change message."""
        return "My Honda Civic from 2019 needs oil change service. When available?"
    
    def create_mock_history_result(
        self, 
        lead_id: str, 
        contact: ContactInfo, 
        message: str, 
        received_at: datetime
    ) -> SimilarityResult:
        """Create a mock similarity result for contact history."""
        metadata = {
            "lead_id": lead_id,
            "message": message,
            "contact_email": str(contact.email) if contact.email else None,
            "contact_phone": contact.phone,
            "contact_name": contact.full_name,
            "received_at": received_at.replace(tzinfo=timezone.utc).isoformat().replace('+00:00', 'Z')
        }
        
        return SimilarityResult(
            lead_id=lead_id,
            similarity_score=1.0,  # Same contact = perfect match
            metadata=metadata
        )

    @pytest.mark.asyncio
    async def test_calculate_message_similarity_high(self, analyzer):
        """Test high similarity calculation between similar messages."""
        msg1 = "My 2019 Honda Civic needs an oil change. When can I schedule?"
        msg2 = "My Honda Civic from 2019 needs oil change service. When available?"
        
        similarity = await analyzer.calculate_message_similarity(msg1, msg2)
        assert similarity > 0.8  # Should be highly similar
        assert similarity <= 1.0
    
    @pytest.mark.asyncio
    async def test_calculate_message_similarity_low(self, analyzer):
        """Test low similarity calculation between different messages."""
        msg1 = "My car needs an oil change"
        msg2 = "I need new brake pads installed"
        
        similarity = await analyzer.calculate_message_similarity(msg1, msg2)
        assert similarity < 0.5  # Should be different
        assert similarity >= 0.0
    
    @pytest.mark.asyncio
    async def test_analyze_first_lead_from_contact(self, analyzer, contact_john, oil_change_message):
        """Test analysis of first lead from a contact."""
        lead_input = LeadInput(
            message=oil_change_message,
            contact=contact_john,
            source=LeadSource.WEB_FORM
        )
        
        # No contact history
        contact_history = []
        
        result = await analyzer.analyze_lead_for_duplicates(lead_input, contact_history)
        
        assert result.action == "process"
        assert result.customer_sequence == 1
        assert "First lead" in result.reason
        assert result.parent_lead_id is None
        assert len(result.related_leads) == 0
    
    @pytest.mark.asyncio 
    async def test_analyze_suspicious_duplicate(
        self, analyzer, contact_john, oil_change_message, similar_oil_change_message
    ):
        """Test flagging of suspicious duplicate within short time window."""
        # Create contact history with recent similar lead
        recent_time = datetime.now(timezone.utc) - timedelta(minutes=30)  # 30 minutes ago
        history = [
            self.create_mock_history_result(
                str(uuid4()), contact_john, oil_change_message, recent_time
            )
        ]
        
        # New similar lead
        new_lead = LeadInput(
            message=similar_oil_change_message,
            contact=contact_john,
            source=LeadSource.WEB_FORM
        )
        
        result = await analyzer.analyze_lead_for_duplicates(new_lead, history)
        
        assert result.action == "flag"
        assert result.customer_sequence == 2
        assert "Suspicious duplicate" in result.reason
        assert result.parent_lead_id is not None
        assert result.time_since_last == 30
        assert len(result.related_leads) == 1
    
    @pytest.mark.asyncio
    async def test_analyze_related_inquiry(
        self, analyzer, contact_john, oil_change_message, brake_repair_message  
    ):
        """Test linking of related inquiry from same contact."""
        # Create contact history with different service request
        few_hours_ago = datetime.now(timezone.utc) - timedelta(hours=4)
        history = [
            self.create_mock_history_result(
                str(uuid4()), contact_john, oil_change_message, few_hours_ago
            )
        ]
        
        # New different service request
        new_lead = LeadInput(
            message=brake_repair_message,
            contact=contact_john,
            source=LeadSource.WEB_FORM  
        )
        
        result = await analyzer.analyze_lead_for_duplicates(new_lead, history)
        
        # Similarity might be low, but same contact within timeframe
        if result.action == "link":
            assert result.customer_sequence == 2
            assert "Related inquiry" in result.reason or "New inquiry" in result.reason
            assert result.parent_lead_id is not None
            assert result.time_since_last == 240  # 4 hours in minutes
        else:
            # If similarity too low, should process as new
            assert result.action == "process"
            assert result.customer_sequence == 2
    
    @pytest.mark.asyncio
    async def test_analyze_new_inquiry_after_time_window(
        self, analyzer, contact_john, oil_change_message, brake_repair_message
    ):
        """Test processing new inquiry after time window expires."""
        # Create contact history beyond time window  
        two_days_ago = datetime.now(timezone.utc) - timedelta(days=2)
        history = [
            self.create_mock_history_result(
                str(uuid4()), contact_john, oil_change_message, two_days_ago
            )
        ]
        
        # New service request
        new_lead = LeadInput(
            message=brake_repair_message,
            contact=contact_john,
            source=LeadSource.WEB_FORM
        )
        
        result = await analyzer.analyze_lead_for_duplicates(new_lead, history)
        
        assert result.action == "process"
        assert result.customer_sequence == 2
        assert "New inquiry" in result.reason
        assert result.time_since_last == 2880  # 2 days in minutes
        assert len(result.related_leads) == 1  # Still tracks history
    
    @pytest.mark.asyncio
    async def test_analyze_multiple_contact_history(
        self, analyzer, contact_john, oil_change_message, brake_repair_message
    ):
        """Test analysis with multiple previous leads from same contact."""
        # Create multiple contact history entries
        one_week_ago = datetime.now(timezone.utc) - timedelta(days=7)
        three_days_ago = datetime.now(timezone.utc) - timedelta(days=3)
        
        history = [
            self.create_mock_history_result(
                str(uuid4()), contact_john, oil_change_message, one_week_ago
            ),
            self.create_mock_history_result(
                str(uuid4()), contact_john, brake_repair_message, three_days_ago  
            )
        ]
        
        # New service request
        new_message = "Need tire rotation and alignment check"
        new_lead = LeadInput(
            message=new_message,
            contact=contact_john,
            source=LeadSource.WEB_FORM
        )
        
        result = await analyzer.analyze_lead_for_duplicates(new_lead, history)
        
        assert result.action == "process"  # Different service, outside suspicious window
        assert result.customer_sequence == 3  # Third lead from this contact
        assert len(result.related_leads) == 2  # Tracks both previous leads
        assert result.time_since_last == 4320  # 3 days in minutes
    
    @pytest.mark.asyncio
    async def test_different_contacts_similar_messages(
        self, analyzer, contact_john, contact_jane, oil_change_message
    ):
        """Test that different contacts with similar messages are processed separately."""
        # Create history for John  
        history_john = [
            self.create_mock_history_result(
                str(uuid4()), contact_john, oil_change_message, datetime.now(timezone.utc) - timedelta(minutes=30)
            )
        ]
        
        # Jane requests similar service
        new_lead_jane = LeadInput(
            message=oil_change_message,  # Same message
            contact=contact_jane,  # Different contact
            source=LeadSource.WEB_FORM
        )
        
        result = await analyzer.analyze_lead_for_duplicates(new_lead_jane, history_john)
        
        # Should process as new since it's a different contact
        # The contact history shouldn't match Jane's contact info
        assert result.action == "process"
        assert result.customer_sequence == 1  # First from Jane's contact
        assert "First lead" in result.reason or "New inquiry" in result.reason
    
    @pytest.mark.asyncio
    async def test_contact_matching_email(self, analyzer):
        """Test contact matching based on email address."""
        contact1 = ContactInfo(
            first_name="John",
            last_name="Doe",
            email="john.doe@email.com",
            phone="5551234567"
        )
        
        # Same email, different phone
        contact2 = ContactInfo(
            first_name="John",
            last_name="Doe", 
            email="john.doe@email.com",
            phone="5559999999"  # Different phone
        )
        
        metadata = {
            "contact_email": "john.doe@email.com",
            "contact_phone": "5551234567",
            "contact_name": "John Doe"
        }
        
        # Should match based on email even with different phone
        assert analyzer._is_same_contact_from_metadata(contact2, metadata)
    
    @pytest.mark.asyncio
    async def test_contact_matching_phone(self, analyzer):
        """Test contact matching based on phone number."""
        contact1 = ContactInfo(
            first_name="John",
            last_name="Doe",
            email="john.doe@email.com",
            phone="5551234567"
        )
        
        # Same phone, different email
        contact2 = ContactInfo(
            first_name="John", 
            last_name="Doe",
            email="john.different@email.com",  # Different email
            phone="5551234567"
        )
        
        metadata = {
            "contact_email": "john.doe@email.com",
            "contact_phone": "5551234567", 
            "contact_name": "John Doe"
        }
        
        # Should match based on phone even with different email
        assert analyzer._is_same_contact_from_metadata(contact2, metadata)
    
    @pytest.mark.asyncio
    async def test_contact_no_match_different_info(self, analyzer):
        """Test that completely different contacts don't match."""
        contact1 = ContactInfo(
            first_name="John",
            last_name="Doe",
            email="john.doe@email.com",
            phone="5551234567"
        )
        
        contact2 = ContactInfo(
            first_name="Jane",
            last_name="Smith",
            email="jane.smith@email.com",
            phone="5559876543"
        )
        
        metadata = {
            "contact_email": "john.doe@email.com",
            "contact_phone": "5551234567",
            "contact_name": "John Doe"
        }
        
        # Should not match completely different contact
        assert not analyzer._is_same_contact_from_metadata(contact2, metadata)


class TestDuplicateAnalysisResult:
    """Test duplicate analysis result class."""
    
    def test_result_creation(self):
        """Test creating analysis result."""
        parent_id = uuid4()
        related_ids = [uuid4(), uuid4()]
        
        result = DuplicateAnalysisResult(
            action="link",
            reason="Related inquiry from same contact",
            related_leads=related_ids,
            parent_lead_id=parent_id,
            customer_sequence=2,
            time_since_last=120,
            message_similarity=0.75
        )
        
        assert result.action == "link"
        assert result.reason == "Related inquiry from same contact"
        assert len(result.related_leads) == 2
        assert result.parent_lead_id == parent_id
        assert result.customer_sequence == 2
        assert result.time_since_last == 120
        assert result.message_similarity == 0.75
    
    def test_result_defaults(self):
        """Test result with default values."""
        result = DuplicateAnalysisResult(
            action="process",
            reason="First lead from contact"
        )
        
        assert result.action == "process"
        assert result.reason == "First lead from contact"
        assert len(result.related_leads) == 0
        assert result.parent_lead_id is None
        assert result.customer_sequence == 1
        assert result.time_since_last is None
        assert result.message_similarity is None
    
    def test_result_repr(self):
        """Test string representation of result."""
        result = DuplicateAnalysisResult(
            action="flag",
            reason="Suspicious duplicate"
        )
        
        repr_str = repr(result)
        assert "flag" in repr_str
        assert "Suspicious duplicate" in repr_str


class TestDuplicateDetectionScenarios:
    """Integration tests for common business scenarios."""
    
    @pytest.mark.asyncio
    async def test_automotive_oil_change_scenario(self):
        """Test the original oil change duplicate scenario that was reported."""
        analyzer = SmartDuplicateAnalyzer()
        
        # Alice Johnson submits oil change request
        alice = ContactInfo(
            first_name="Alice",
            last_name="Johnson",
            email="alice.johnson@email.com",
            phone="5551111111"
        )
        
        alice_message = "My 2019 Honda Civic needs an oil change. When can I schedule an appointment?"
        
        # Bob Williams submits similar oil change request 
        bob = ContactInfo(
            first_name="Bob", 
            last_name="Williams",
            email="bob.williams@email.com",
            phone="5552222222"
        )
        
        bob_message = "I need an oil change for my Honda Civic. What times are available?"
        
        # Simulate Alice's lead being processed first (no history)
        alice_lead = LeadInput(message=alice_message, contact=alice)
        alice_result = await analyzer.analyze_lead_for_duplicates(alice_lead, [])
        
        assert alice_result.action == "process"
        assert alice_result.customer_sequence == 1
        
        # Simulate Bob's lead being processed with no relevant contact history
        # (Alice's history wouldn't be returned by find_leads_by_contact for Bob)
        # This simulates the real system where contact history is filtered by contact info
        
        bob_lead = LeadInput(message=bob_message, contact=bob)
        bob_result = await analyzer.analyze_lead_for_duplicates(bob_lead, [])  # Empty history for Bob
        
        # Bob should be processed as new since he has no contact history
        assert bob_result.action == "process" 
        assert bob_result.customer_sequence == 1  # First from Bob's contact
        assert "First lead" in bob_result.reason
    
    @pytest.mark.asyncio
    async def test_medspa_follow_up_scenario(self):
        """Test medical spa follow-up inquiry scenario."""
        analyzer = SmartDuplicateAnalyzer()
        
        sarah = ContactInfo(
            first_name="Sarah",
            last_name="Chen",
            email="sarah.chen@email.com", 
            phone="5553333333"
        )
        
        # First inquiry about Botox
        initial_message = "I'm interested in Botox treatment. What's the consultation process?"
        
        # Follow-up question about pricing
        followup_message = "Hi, I called earlier about Botox. Can you send me pricing information?"
        
        # Create history with initial inquiry
        initial_time = datetime.now(timezone.utc) - timedelta(hours=2)
        history = [
            SimilarityResult(
                lead_id=uuid4(),
                similarity_score=1.0,
                metadata={
                    "lead_id": str(uuid4()),
                    "message": initial_message,
                    "contact_email": str(sarah.email),
                    "contact_phone": sarah.phone,
                    "contact_name": sarah.full_name,
                    "received_at": initial_time.replace(tzinfo=timezone.utc).isoformat().replace('+00:00', 'Z')
                }
            )
        ]
        
        # Follow-up lead
        followup_lead = LeadInput(message=followup_message, contact=sarah)
        result = await analyzer.analyze_lead_for_duplicates(followup_lead, history)
        
        # Should be processed as new inquiry (similarity 0.72 < threshold 0.8)
        # but still track as follow-up from same contact
        assert result.action == "process"  # Different enough message = process as new
        assert result.customer_sequence == 2
        assert result.time_since_last == 120  # 2 hours
        assert len(result.related_leads) == 1  # Still tracks previous inquiry
    
    @pytest.mark.asyncio  
    async def test_accidental_duplicate_submission(self):
        """Test catching accidental duplicate submissions."""
        analyzer = SmartDuplicateAnalyzer()
        
        customer = ContactInfo(
            first_name="Mike",
            last_name="Davis",
            email="mike.davis@email.com",
            phone="5554444444"
        )
        
        # Same message submitted twice quickly (form double-click)
        message = "I need brake repair service. My car is making grinding noises."
        
        # First submission 5 minutes ago
        first_time = datetime.now(timezone.utc) - timedelta(minutes=5)
        history = [
            SimilarityResult(
                lead_id=uuid4(),
                similarity_score=1.0,
                metadata={
                    "lead_id": str(uuid4()),
                    "message": message,
                    "contact_email": str(customer.email),
                    "contact_phone": customer.phone,
                    "contact_name": customer.full_name,
                    "received_at": first_time.replace(tzinfo=timezone.utc).isoformat().replace('+00:00', 'Z')
                }
            )
        ]
        
        # Duplicate submission
        duplicate_lead = LeadInput(message=message, contact=customer)
        result = await analyzer.analyze_lead_for_duplicates(duplicate_lead, history)
        
        # Should be flagged as suspicious duplicate
        assert result.action == "flag"
        assert result.customer_sequence == 2
        assert "Suspicious duplicate" in result.reason
        assert result.time_since_last == 5
        assert result.message_similarity >= 0.9
    
    @pytest.mark.asyncio
    async def test_user_reported_scenario_3_minute_window(self):
        """Test the exact user scenario: same contact info with slight message variation within 3 minutes."""
        analyzer = SmartDuplicateAnalyzer()
        
        # Customer contact info
        customer = ContactInfo(
            first_name="Jennifer",
            last_name="Martinez",
            email="jennifer.martinez@email.com",
            phone="5556667777"
        )
        
        # First message
        first_message = "I need an oil change for my car. When are you available this week?"
        
        # Slightly different message (user resubmitted with variation)
        second_message = "I need an oil change for my vehicle. When are you available this week?"
        
        # First submission 3 minutes ago
        first_time = datetime.now(timezone.utc) - timedelta(minutes=3)
        history = [
            SimilarityResult(
                lead_id=str(uuid4()),
                similarity_score=1.0,
                metadata={
                    "lead_id": str(uuid4()),
                    "message": first_message,
                    "contact_email": str(customer.email),
                    "contact_phone": customer.phone,
                    "contact_name": customer.full_name,
                    "received_at": first_time.replace(tzinfo=timezone.utc).isoformat().replace('+00:00', 'Z')
                }
            )
        ]
        
        # Second submission (slightly different message, same contact, 3 minutes later)
        second_lead = LeadInput(message=second_message, contact=customer)
        result = await analyzer.analyze_lead_for_duplicates(second_lead, history)
        
        # With new thresholds (0.85 suspicious threshold, 180min window), this should be flagged
        # Message similarity should be > 0.85, and 3 minutes is < 180 minutes
        assert result.action == "flag"  # Should be flagged as suspicious duplicate
        assert result.customer_sequence == 2
        assert "Suspicious duplicate" in result.reason
        assert result.time_since_last == 3
        assert result.message_similarity > 0.95  # Should be very similar (car vs vehicle)
        assert result.parent_lead_id is not None
        assert len(result.related_leads) == 1