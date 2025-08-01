"""Airtable CRM integration service for baseCamp application."""

import asyncio
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from uuid import UUID

import httpx
from pyairtable import Api, Base, Table
from pyairtable.api.types import CreateRecordDict, UpdateRecordDict
from pyairtable.exceptions import PyAirtableError

from ..config.settings import settings
from ..models.airtable import (
    AirtableConfig,
    AirtableFieldMapping,
    AirtableRecord,
    SyncBatch,
    SyncOperation,
    SyncRecord,
    SyncStatus,
    WebhookPayload
)
from ..models.lead import EnrichedLead


class CRMServiceError(Exception):
    """Base exception for CRM service errors."""
    pass


class AirtableConnectionError(CRMServiceError):
    """Error connecting to Airtable API."""
    pass


class AirtableRateLimitError(CRMServiceError):
    """Airtable API rate limit exceeded."""
    pass


class AirtableConfigError(CRMServiceError):
    """Airtable configuration error."""
    pass


class CRMServiceInterface(ABC):
    """Abstract interface for CRM services."""
    
    @abstractmethod
    async def sync_lead(self, lead: EnrichedLead) -> SyncRecord:
        """Sync a single lead to CRM."""
        pass
    
    @abstractmethod
    async def sync_leads_batch(self, leads: List[EnrichedLead]) -> SyncBatch:
        """Sync multiple leads to CRM in batch."""
        pass
    
    @abstractmethod
    async def update_lead(self, lead: EnrichedLead) -> SyncRecord:
        """Update existing lead in CRM."""
        pass
    
    @abstractmethod
    async def delete_lead(self, lead_id: UUID) -> bool:
        """Delete lead from CRM."""
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Check if CRM service is available."""
        pass


class AirtableService(CRMServiceInterface):
    """Airtable implementation of CRM service."""
    
    def __init__(self, config: Optional[AirtableConfig] = None):
        self.logger = logging.getLogger(__name__)
        
        # Initialize configuration
        if config:
            self.config = config
        else:
            self.config = self._load_config_from_settings()
        
        # Initialize Airtable API
        self.api = None
        self.base = None
        self.table = None
        self._initialize_airtable_client()
        
        # Rate limiting
        self.rate_limit_delay = 0.2  # 200ms between requests (5 requests/second)
        self.last_request_time = 0.0
    
    def _load_config_from_settings(self) -> AirtableConfig:
        """Load Airtable configuration from application settings."""
        if not settings.airtable_configured:
            raise AirtableConfigError("Airtable not configured in settings")
        
        return AirtableConfig(
            base_id=settings.airtable_base_id,
            table_name=settings.airtable_table_name,
            api_key=settings.airtable_api_key,
            field_mapping=AirtableFieldMapping()
        )
    
    def _initialize_airtable_client(self):
        """Initialize Airtable API client."""
        try:
            self.api = Api(api_key=self.config.api_key)
            self.base = self.api.base(self.config.base_id)
            self.table = self.base.table(self.config.table_name)
            
            self.logger.info(
                f"Airtable client initialized for base {self.config.base_id}, "
                f"table {self.config.table_name}"
            )
        except Exception as e:
            self.logger.error(f"Failed to initialize Airtable client: {str(e)}")
            raise AirtableConnectionError(f"Airtable initialization failed: {str(e)}")
    
    async def _rate_limit(self):
        """Apply rate limiting to API requests."""
        current_time = asyncio.get_event_loop().time()
        time_since_last_request = current_time - self.last_request_time
        
        if time_since_last_request < self.rate_limit_delay:
            wait_time = self.rate_limit_delay - time_since_last_request
            await asyncio.sleep(wait_time)
        
        self.last_request_time = asyncio.get_event_loop().time()
    
    async def sync_lead(self, lead: EnrichedLead) -> SyncRecord:
        """Sync a single lead to Airtable."""
        sync_record = SyncRecord(
            lead_id=lead.id,
            operation=SyncOperation.CREATE,
            base_id=self.config.base_id,
            table_name=self.config.table_name,
            max_retries=self.config.max_retries
        )
        
        try:
            sync_record.mark_started()
            
            # Check if lead already exists in Airtable
            existing_record_id = lead.external_ids.get("airtable")
            if existing_record_id:
                sync_record.operation = SyncOperation.UPDATE
                return await self._update_existing_record(lead, sync_record, existing_record_id)
            else:
                return await self._create_new_record(lead, sync_record)
                
        except Exception as e:
            error_msg = f"Failed to sync lead {lead.id}: {str(e)}"
            self.logger.error(error_msg)
            sync_record.mark_failed(error_msg)
            return sync_record
    
    async def _create_new_record(self, lead: EnrichedLead, sync_record: SyncRecord) -> SyncRecord:
        """Create new record in Airtable."""
        try:
            await self._rate_limit()
            
            # Create Airtable record from lead
            airtable_record = AirtableRecord.from_enriched_lead(
                lead, 
                self.config.field_mapping
            )
            
            # Prepare data for Airtable API
            create_data: CreateRecordDict = {
                "fields": airtable_record.fields
            }
            
            # Store snapshot for debugging
            sync_record.data_snapshot = create_data
            
            # Create record in Airtable
            created_record = self.table.create(create_data["fields"])
            
            # Update sync record with success
            sync_record.mark_success(created_record["id"])
            
            self.logger.info(
                f"Successfully created Airtable record {created_record['id']} "
                f"for lead {lead.id}"
            )
            
            return sync_record
            
        except PyAirtableError as e:
            if "RATE_LIMITED" in str(e):
                raise AirtableRateLimitError(f"Rate limit exceeded: {str(e)}")
            else:
                raise AirtableConnectionError(f"Airtable API error: {str(e)}")
        except Exception as e:
            raise CRMServiceError(f"Unexpected error creating record: {str(e)}")
    
    async def _update_existing_record(
        self, 
        lead: EnrichedLead, 
        sync_record: SyncRecord,
        record_id: str
    ) -> SyncRecord:
        """Update existing record in Airtable."""
        try:
            await self._rate_limit()
            
            # Create Airtable record from lead
            airtable_record = AirtableRecord.from_enriched_lead(
                lead, 
                self.config.field_mapping,
                record_id
            )
            
            # Prepare data for Airtable API
            update_data: UpdateRecordDict = {
                "id": record_id,
                "fields": airtable_record.fields
            }
            
            # Store snapshot for debugging
            sync_record.data_snapshot = update_data
            
            # Update record in Airtable
            updated_record = self.table.update(record_id, update_data["fields"])
            
            # Update sync record with success
            sync_record.mark_success(updated_record["id"])
            
            self.logger.info(
                f"Successfully updated Airtable record {record_id} "
                f"for lead {lead.id}"
            )
            
            return sync_record
            
        except PyAirtableError as e:
            if "RATE_LIMITED" in str(e):
                raise AirtableRateLimitError(f"Rate limit exceeded: {str(e)}")
            elif "NOT_FOUND" in str(e):
                # Record doesn't exist, create new one
                self.logger.warning(f"Record {record_id} not found, creating new record")
                sync_record.operation = SyncOperation.CREATE
                return await self._create_new_record(lead, sync_record)
            else:
                raise AirtableConnectionError(f"Airtable API error: {str(e)}")
        except Exception as e:
            raise CRMServiceError(f"Unexpected error updating record: {str(e)}")
    
    async def sync_leads_batch(self, leads: List[EnrichedLead]) -> SyncBatch:
        """Sync multiple leads to Airtable in batch."""
        if not leads:
            raise ValueError("Cannot sync empty leads list")
        
        batch_id = f"batch_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{len(leads)}"
        
        # Create sync records for each lead
        sync_operations = []
        for lead in leads:
            sync_record = SyncRecord(
                lead_id=lead.id,
                operation=SyncOperation.CREATE if not lead.external_ids.get("airtable") else SyncOperation.UPDATE,
                base_id=self.config.base_id,
                table_name=self.config.table_name,
                max_retries=self.config.max_retries
            )
            sync_operations.append(sync_record)
        
        batch = SyncBatch(
            batch_id=batch_id,
            operations=sync_operations,
            total_operations=len(leads)
        )
        
        batch.mark_started()
        self.logger.info(f"Starting batch sync {batch_id} with {len(leads)} leads")
        
        # Process leads in smaller chunks to respect Airtable limits
        chunk_size = min(self.config.batch_size, 10)  # Airtable max 10 records per batch
        
        for i in range(0, len(leads), chunk_size):
            chunk_leads = leads[i:i + chunk_size]
            chunk_operations = sync_operations[i:i + chunk_size]
            
            try:
                await self._process_batch_chunk(chunk_leads, chunk_operations)
            except Exception as e:
                self.logger.error(f"Error processing batch chunk {i//chunk_size + 1}: {str(e)}")
                # Mark remaining operations as failed
                for op in chunk_operations:
                    if op.status == SyncStatus.PENDING:
                        op.mark_failed(f"Batch processing failed: {str(e)}")
        
        batch.mark_completed()
        
        self.logger.info(
            f"Batch sync {batch_id} completed: "
            f"{batch.successful_operations}/{batch.total_operations} successful "
            f"({batch.success_rate:.1f}%)"
        )
        
        return batch
    
    async def _process_batch_chunk(
        self, 
        leads: List[EnrichedLead], 
        operations: List[SyncRecord]
    ):
        """Process a chunk of leads in batch."""
        try:
            await self._rate_limit()
            
            # Separate creates and updates
            creates = []
            updates = []
            create_ops = []
            update_ops = []
            
            for lead, operation in zip(leads, operations):
                operation.mark_started()
                
                airtable_record = AirtableRecord.from_enriched_lead(
                    lead, 
                    self.config.field_mapping
                )
                
                if operation.operation == SyncOperation.CREATE:
                    creates.append(airtable_record.fields)
                    create_ops.append(operation)
                else:
                    existing_id = lead.external_ids.get("airtable")
                    if existing_id:
                        airtable_record.record_id = existing_id
                        updates.append({
                            "id": existing_id,
                            "fields": airtable_record.fields
                        })
                        update_ops.append(operation)
            
            # Process creates
            if creates:
                try:
                    created_records = self.table.batch_create(creates)
                    for record, operation in zip(created_records, create_ops):
                        operation.mark_success(record["id"])
                except PyAirtableError as e:
                    error_msg = f"Batch create failed: {str(e)}"
                    for operation in create_ops:
                        operation.mark_failed(error_msg)
            
            # Process updates
            if updates:
                try:
                    updated_records = self.table.batch_update(updates)
                    for record, operation in zip(updated_records, update_ops):
                        operation.mark_success(record["id"])
                except PyAirtableError as e:
                    error_msg = f"Batch update failed: {str(e)}"
                    for operation in update_ops:
                        operation.mark_failed(error_msg)
                        
        except Exception as e:
            error_msg = f"Batch chunk processing failed: {str(e)}"
            for operation in operations:
                if operation.status in [SyncStatus.PENDING, SyncStatus.IN_PROGRESS]:
                    operation.mark_failed(error_msg)
            raise
    
    async def update_lead(self, lead: EnrichedLead) -> SyncRecord:
        """Update existing lead in Airtable."""
        existing_record_id = lead.external_ids.get("airtable")
        if not existing_record_id:
            # No existing record, create new one
            return await self.sync_lead(lead)
        
        sync_record = SyncRecord(
            lead_id=lead.id,
            operation=SyncOperation.UPDATE,
            airtable_record_id=existing_record_id,
            base_id=self.config.base_id,
            table_name=self.config.table_name,
            max_retries=self.config.max_retries
        )
        
        try:
            sync_record.mark_started()
            return await self._update_existing_record(lead, sync_record, existing_record_id)
        except Exception as e:
            error_msg = f"Failed to update lead {lead.id}: {str(e)}"
            self.logger.error(error_msg)
            sync_record.mark_failed(error_msg)
            return sync_record
    
    async def delete_lead(self, lead_id: UUID) -> bool:
        """Delete lead from Airtable."""
        try:
            # Note: This requires knowing the Airtable record ID
            # In practice, you'd need to look this up from your lead storage
            self.logger.warning(f"Delete operation requested for lead {lead_id} - not implemented")
            return False
        except Exception as e:
            self.logger.error(f"Failed to delete lead {lead_id}: {str(e)}")
            return False
    
    async def health_check(self) -> bool:
        """Check if Airtable service is available."""
        try:
            await self._rate_limit()
            
            # Try to get table schema
            table_info = self.table.schema()
            
            if table_info and "fields" in table_info:
                self.logger.info("Airtable health check passed")
                return True
            else:
                self.logger.error("Airtable health check failed - invalid schema response")
                return False
                
        except Exception as e:
            self.logger.error(f"Airtable health check failed: {str(e)}")
            return False
    
    def get_field_mapping_validation(self) -> Dict[str, bool]:
        """Validate field mapping against Airtable schema."""
        try:
            schema = self.table.schema()
            field_names = [field["name"] for field in schema.get("fields", [])]
            
            mapping = self.config.field_mapping
            validation_results = {}
            
            # Check core fields
            validation_results["first_name_field"] = mapping.first_name_field in field_names
            validation_results["last_name_field"] = mapping.last_name_field in field_names
            validation_results["email_field"] = mapping.email_field in field_names
            validation_results["phone_field"] = mapping.phone_field in field_names
            validation_results["message_field"] = mapping.message_field in field_names
            validation_results["source_field"] = mapping.source_field in field_names
            validation_results["intent_field"] = mapping.intent_field in field_names
            validation_results["urgency_field"] = mapping.urgency_field in field_names
            validation_results["quality_score_field"] = mapping.quality_score_field in field_names
            validation_results["received_at_field"] = mapping.received_at_field in field_names
            validation_results["status_field"] = mapping.status_field in field_names
            validation_results["lead_id_field"] = mapping.lead_id_field in field_names
            
            # Check custom fields
            for airtable_field in mapping.custom_fields.values():
                validation_results[f"custom_{airtable_field}"] = airtable_field in field_names
            
            return validation_results
            
        except Exception as e:
            self.logger.error(f"Failed to validate field mapping: {str(e)}")
            return {"error": str(e)}
    
    async def process_webhook(self, payload: WebhookPayload) -> Dict[str, int]:
        """Process incoming webhook from Airtable."""
        try:
            # Get table ID from schema (this would need to be stored/cached)
            # For now, we'll just log the webhook
            self.logger.info(f"Received Airtable webhook for base {payload.base}")
            
            # Count changes by type
            stats = {
                "created": 0,
                "updated": 0,
                "deleted": 0
            }
            
            # Process each table
            for table_id, changes in payload.changed_tables_by_id.items():
                stats["updated"] += len(changes.get("records", []))
            
            for table_id, creates in payload.created_tables_by_id.items():
                stats["created"] += len(creates.get("records", []))
            
            for table_id, deletes in payload.destroyed_tables_by_id.items():
                stats["deleted"] += len(deletes.get("records", []))
            
            self.logger.info(f"Webhook processed: {stats}")
            return stats
            
        except Exception as e:
            self.logger.error(f"Failed to process webhook: {str(e)}")
            return {"error": str(e)}


# Factory function for creating CRM service
def create_crm_service(config: Optional[AirtableConfig] = None) -> CRMServiceInterface:
    """Create and return appropriate CRM service instance."""
    return AirtableService(config)


# Singleton instance for dependency injection
_crm_service: Optional[CRMServiceInterface] = None


async def get_crm_service() -> CRMServiceInterface:
    """Get or create CRM service instance."""
    global _crm_service
    if _crm_service is None:
        _crm_service = create_crm_service()
    return _crm_service