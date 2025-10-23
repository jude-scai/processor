"""
Base Processor Module

Provides abstract base class for all processor implementations with standardized
3-phase execution pipeline (pre-extraction, extraction, post-extraction) and
atomic success/failure semantics.
"""

import hashlib
import json
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Optional

from .exceptions import (
    PrevalidationError,
    InputValidationError,
    TransformationError,
    FactorExtractionError,
    ResultValidationError,
)
from .models import (
    ExecutionStatus,
    ProcessorType,
    ProcessingResult,
    ExecutionPayload,
    ValidationResult,
)
from .repositories.processor_repository import ProcessorRepository
from .repositories.execution_repository import ExecutionRepository


class BaseProcessor(ABC):
    """
    Abstract base class for all processor implementations.

    Implements the 3-phase execution pipeline:
    1. Pre-extraction: prevalidate, transform, validate input
    2. Extraction: extract factors from validated inputs
    3. Post-extraction: validate output, persist results

    Enforces atomic success/failure semantics - all inputs must succeed
    or the entire execution fails.

    Subclasses must define:
    - PROCESSOR_NAME: Unique identifier for the processor
    - PROCESSOR_TYPE: Type of processor (application/stipulation/document)
    - PROCESSOR_TRIGGERS: What inputs trigger execution
    - CONFIG (optional): Default configuration values

    Subclasses must implement:
    - transform_input(): Transform raw inputs to standardized format
    - validate_input(): Validate transformed inputs
    - extract(): Extract factors from validated inputs
    - validate_output(): Validate extraction outputs
    """

    # Configuration constants (must be defined by subclasses)
    PROCESSOR_NAME: str
    PROCESSOR_TYPE: ProcessorType
    PROCESSOR_TRIGGERS: dict[str, list[str]] = {}
    CONFIG: dict[str, Any] = {}

    def __init__(
        self,
        processor_repo: Optional[ProcessorRepository] = None,
        execution_repo: Optional[ExecutionRepository] = None
    ):
        """
        Initialize the processor with cost tracking and repository connections.

        Args:
            processor_repo: Repository for processor configuration operations
            execution_repo: Repository for execution management operations
        """
        self._total_cost: float = 0.0
        self._cost_breakdown: dict[str, float] = {}
        self._execution_id: str | None = None
        self._underwriting_processor_id: str | None = None
        self._document_revision_ids: list[str] = []
        self._document_ids_hash: str | None = None

        # Repository connections
        self._processor_repo = processor_repo
        self._execution_repo = execution_repo

    # =====================================================================
    # CONFIGURATION
    # =====================================================================

    def get_config(self) -> dict[str, Any]:
        """
        Get effective configuration by merging defaults with database overrides.

        Configuration resolution order (right-side precedence):
        1. System defaults (self.CONFIG from code)
        2. Tenant overrides (purchased_processors.config)
        3. Underwriting overrides (underwriting_processors.config_override)

        Requires that the processor was initialized with processor_repo and
        _underwriting_processor_id was set.

        Returns:
            Merged configuration dictionary with all levels applied

        Raises:
            ValueError: If processor_repo or underwriting_processor_id not set
        """
        if not self._processor_repo:
            raise ValueError(
                "Processor repository not initialized. "
                "Pass processor_repo to __init__() to enable configuration fetching."
            )

        if not self._underwriting_processor_id:
            raise ValueError(
                "Underwriting processor ID not set. "
                "Set _underwriting_processor_id before calling get_config()."
            )

        # Start with system defaults from processor class
        default_config = self.CONFIG if hasattr(self, "CONFIG") else {}

        # Get effective config from database (tenant + underwriting overrides)
        db_config = self._processor_repo.get_effective_config(self._underwriting_processor_id)

        # Merge: system defaults < database config
        return {**default_config, **db_config}

    # =====================================================================
    # STATIC METHODS (Optional overrides)
    # =====================================================================

    @staticmethod
    def should_execute(payload: dict[str, Any]) -> tuple[bool, str | None]:
        """
        Determine if processor should execute based on custom business logic.

        Override this method to implement custom execution eligibility rules
        beyond trigger matching (e.g., minimum document count requirements).

        Args:
            payload: The execution payload

        Returns:
            Tuple of (should_execute: bool, reason: str | None)
            If False, reason explains why execution was skipped
        """
        return True, None

    @staticmethod
    def consolidate(executions: list[Any]) -> dict[str, Any]:
        """
        Consolidate multiple execution outputs into final factors.

        Override this method for processors that can have multiple executions
        (e.g., bank statements across multiple months that need averaging).

        Default behavior: Return the last execution's output, or empty dict if none.

        Args:
            executions: List of active execution records with .output attributes

        Returns:
            Consolidated factors dictionary
        """
        if not executions:
            return {}
        if len(executions) == 1:
            return executions[0].output or {}
        return executions[-1].output or {}

    # =====================================================================
    # FORMAT PAYLOAD LIST (For Orchestration)
    # =====================================================================
    
    def format_payload_list(self, underwriting_data: dict[str, Any]) -> list[dict[str, Any]]:
        """
        Format underwriting data into list of payloads for execution.
        
        Implementation varies based on processor type:
        - APPLICATION: Single payload with application form fields
        - STIPULATION: Single payload with all matching document revisions
        - DOCUMENT: One payload per matching document revision
        
        Args:
            underwriting_data: Complete underwriting data including merchant and owners
            
        Returns:
            List of payload dictionaries, or empty list if no triggers matched
        """
        if self.PROCESSOR_TYPE == ProcessorType.APPLICATION:
            return self._format_application_payload(underwriting_data)
        elif self.PROCESSOR_TYPE == ProcessorType.STIPULATION:
            return self._format_stipulation_payload(underwriting_data)
        elif self.PROCESSOR_TYPE == ProcessorType.DOCUMENT:
            return self._format_document_payload(underwriting_data)
        else:
            return []
    
    def _format_application_payload(self, underwriting_data: dict[str, Any]) -> list[dict[str, Any]]:
        """Format payload for APPLICATION type processor."""
        # Get trigger fields from PROCESSOR_TRIGGERS
        trigger_fields = self.PROCESSOR_TRIGGERS.get('application_form', [])
        
        # Build application form from underwriting merchant fields
        application_form = {}
        merchant = underwriting_data.get('merchant', {})
        
        # Map merchant fields to dot notation
        field_mapping = {
            'name': 'merchant.name',
            'ein': 'merchant.ein',
            'industry': 'merchant.industry',
            'email': 'merchant.email',
            'phone': 'merchant.phone',
            'website': 'merchant.website',
            'entity_type': 'merchant.entity_type',
            'incorporation_date': 'merchant.incorporation_date',
            'state_of_incorporation': 'merchant.state_of_incorporation',
        }
        
        for field, dot_key in field_mapping.items():
            value = merchant.get(field)
            if value is not None:
                application_form[dot_key] = value
        
        # Check if all trigger fields are null
        has_data = any(application_form.get(field) is not None for field in trigger_fields)
        
        if not has_data:
            return []
        
        # Return single payload with application form and owners
        return [{
            "application_form": application_form,
            "owners_list": underwriting_data.get('owners', [])
        }]
    
    def _format_stipulation_payload(self, underwriting_data: dict[str, Any]) -> list[dict[str, Any]]:
        """Format payload for STIPULATION type processor."""
        # Get stipulation type from PROCESSOR_TRIGGERS
        trigger_docs = self.PROCESSOR_TRIGGERS.get('documents_list', [])
        
        if not trigger_docs:
            return []
        
        stipulation_type = trigger_docs[0]  # e.g., 's_bank_statement'
        
        # Filter documents by stipulation type
        # Note: underwriting_data doesn't have documents yet - need to query separately
        # For now, return empty (will be enhanced when document integration is added)
        return []
    
    def _format_document_payload(self, underwriting_data: dict[str, Any]) -> list[dict[str, Any]]:
        """Format payload for DOCUMENT type processor."""
        # Get stipulation type from PROCESSOR_TRIGGERS
        trigger_docs = self.PROCESSOR_TRIGGERS.get('documents_list', [])
        
        if not trigger_docs:
            return []
        
        # Filter documents and create one payload per document
        # Note: underwriting_data doesn't have documents yet - need to query separately
        # For now, return empty (will be enhanced when document integration is added)
        return []

    # =====================================================================
    # COST TRACKING
    # =====================================================================

    def _add_cost(self, cost: float, operation_type: str = "general") -> None:
        """
        Add cost for an operation during processing.

        Args:
            cost: Cost amount in cents to add
            operation_type: Category of operation (e.g., "api_call", "document_page")
        """
        self._total_cost += cost
        self._cost_breakdown[operation_type] = (
            self._cost_breakdown.get(operation_type, 0.0) + cost
        )

    def _add_document_revision_id(self, revision_id: str) -> None:
        """
        Track a document revision ID that was processed.

        Args:
            revision_id: Document revision ID to track
        """
        if revision_id not in self._document_revision_ids:
            self._document_revision_ids.append(revision_id)

    def _set_document_ids_hash(self, document_ids: list[str]) -> None:
        """
        Set hash of base document IDs for deduplication.

        Args:
            document_ids: List of base document IDs (not revision IDs)
        """
        if document_ids:
            sorted_ids = sorted(list(set(document_ids)))
            self._document_ids_hash = hashlib.sha256(
                json.dumps(sorted_ids).encode("utf-8")
            ).hexdigest()
        else:
            self._document_ids_hash = None

    # =====================================================================
    # EVENT EMISSION
    # =====================================================================

    def _emit_event(self, event_type: str, payload: dict[str, Any]) -> None:
        """
        Emit lifecycle event to Pub/Sub.

        Events emitted:
        - {PROCESSOR_NAME}.execution.started
        - {PROCESSOR_NAME}.execution.completed
        - {PROCESSOR_NAME}.execution.failed

        Args:
            event_type: Type of event (started, completed, failed)
            payload: Event payload data
        """
        # TODO: Implement actual Pub/Sub emission
        # For now, just log the event
        event_name = f"{self.PROCESSOR_NAME}.execution.{event_type}"
        print(f"[EVENT] {event_name}: {payload}")

    # =====================================================================
    # ABSTRACT METHODS (Must be implemented by subclasses)
    # =====================================================================

    def prevalidate_input(self, payload: ExecutionPayload) -> None:
        """
        Pre-validate inputs before transformation.

        Check if required documents exist and are of correct type.
        This method has a default implementation that does nothing,
        but can be overridden for processor-specific pre-validation.

        Args:
            payload: The raw execution payload

        Raises:
            PrevalidationError: If pre-validation fails
        """
        # Default: no pre-validation required

    @abstractmethod
    def transform_input(self, payload: ExecutionPayload) -> Any:
        """
        Transform and normalize raw input payload.

        This method should:
        - Convert raw inputs into standardized format
        - Handle document splicing, chunking if needed
        - Normalize data structures
        - Pull supplementary data if needed

        Args:
            payload: The raw execution payload

        Returns:
            Transformed data ready for validation

        Raises:
            TransformationError: If transformation fails
        """
        ...

    @abstractmethod
    def validate_input(self, transformed_data: Any) -> ValidationResult:
        """
        Validate transformed input data.

        Verify input structure and required fields are present.
        Check processor-specific requirements.

        Args:
            transformed_data: Output from transform_input()

        Returns:
            ValidationResult indicating if input is valid

        Raises:
            InputValidationError: If validation fails critically
        """
        ...

    @abstractmethod
    def extract(self, validated_data: Any) -> dict[str, Any]:
        """
        Extract factors from validated inputs.

        This is the core processor logic that produces the execution output.

        Args:
            validated_data: Validated input data

        Returns:
            Dictionary of extracted factors/output

        Raises:
            FactorExtractionError: If extraction fails
            ApiError: If external API call fails
            DataTransformationError: If data transformation fails during extraction
        """
        ...

    @abstractmethod
    def validate_output(self, output: dict[str, Any]) -> ValidationResult:
        """
        Validate extraction output.

        Ensure extracted output meets processor-specific requirements.

        Args:
            output: Output from extract()

        Returns:
            ValidationResult indicating if output is valid

        Raises:
            ResultValidationError: If validation fails critically
        """
        ...

    # =====================================================================
    # EXECUTION PIPELINE
    # =====================================================================

    def _phase_preextraction(self, payload: ExecutionPayload) -> Any:
        """
        Phase 1: Pre-extraction

        1. Prevalidate inputs (check document existence and types)
        2. Transform inputs (normalize and prepare data)
        3. Validate transformed inputs

        Returns:
            Prevalidated and transformed data ready for extraction

        Raises:
            PrevalidationError: If input prevalidation fails
            TransformationError: If input transformation fails
            InputValidationError: If transformed inputs are invalid
        """
        # Step 1: Prevalidate inputs
        self.prevalidate_input(payload)

        # Step 2: Transform inputs
        transformed_data = self.transform_input(payload)

        # Step 3: Validate transformed inputs
        validation_result = self.validate_input(transformed_data)
        if not validation_result.is_valid:
            raise InputValidationError(
                f"Input validation failed: {', '.join(validation_result.errors)}",
                processor_name=self.PROCESSOR_NAME
            )

        return transformed_data

    def _phase_extraction(self, transformed_data: Any) -> dict[str, Any]:
        """
        Phase 2: Extraction

        Extract factors from validated inputs.
        All inputs must succeed or entire execution fails.

        Returns:
            Extracted output dictionary

        Raises:
            FactorExtractionError: If extraction fails
            ApiError: If external API call fails
            DataTransformationError: If data transformation fails
        """
        output = self.extract(transformed_data)
        return output

    def _phase_postextraction(self, output: dict[str, Any]) -> dict[str, Any]:
        """
        Phase 3: Post-extraction

        1. Validate extraction output
        2. Return validated output for persistence

        Returns:
            Validated output ready for persistence

        Raises:
            ResultValidationError: If output validation fails
        """
        # Validate output
        validation_result = self.validate_output(output)
        if not validation_result.is_valid:
            raise ResultValidationError(
                f"Output validation failed: {', '.join(validation_result.errors)}",
                processor_name=self.PROCESSOR_NAME
            )

        return output

    def execute(
        self,
        execution_id: str,
        underwriting_processor_id: str,
        payload: ExecutionPayload,
    ) -> ProcessingResult:
        """
        Execute the complete 3-phase processing pipeline.

        Enforces atomic success/failure semantics:
        - All inputs succeed: execution completes successfully
        - Any input fails: entire execution fails immediately

        Args:
            execution_id: Unique execution ID
            underwriting_processor_id: Underwriting processor instance ID
            payload: Input data for execution

        Returns:
            ProcessingResult with execution status and outputs
        """
        self._execution_id = execution_id
        self._underwriting_processor_id = underwriting_processor_id
        started_at = datetime.utcnow()
        status = ExecutionStatus.FAILED
        output: dict[str, Any] = {}
        error_message: str | None = None
        error_type: str | None = None
        error_phase: str | None = None

        # Emit started event
        self._emit_event("started", {
            "execution_id": execution_id,
            "underwriting_processor_id": underwriting_processor_id,
            "processor_name": self.PROCESSOR_NAME,
        })

        try:
            # Phase 1: Pre-extraction
            transformed_data = self._phase_preextraction(payload)

            # Phase 2: Extraction
            output = self._phase_extraction(transformed_data)

            # Phase 3: Post-extraction
            validated_output = self._phase_postextraction(output)
            output = validated_output

            # Success!
            status = ExecutionStatus.COMPLETED
            self._emit_event("completed", {
                "execution_id": execution_id,
                "underwriting_processor_id": underwriting_processor_id,
                "processor_name": self.PROCESSOR_NAME,
                "output_keys": list(output.keys()),
            })

        except (PrevalidationError, InputValidationError, TransformationError) as e:
            error_phase = "pre-extraction"
            error_type = e.__class__.__name__
            error_message = str(e)
            print(f"[ERROR] Pre-extraction failed: {error_message}")

        except FactorExtractionError as e:
            error_phase = "extraction"
            error_type = e.__class__.__name__
            error_message = str(e)
            print(f"[ERROR] Extraction failed: {error_message}")

        except ResultValidationError as e:
            error_phase = "post-extraction"
            error_type = e.__class__.__name__
            error_message = str(e)
            print(f"[ERROR] Post-extraction failed: {error_message}")

        except BaseException as e:  # pragma: no cover
            # Catch all other exceptions including system exceptions
            error_phase = "unknown"
            error_type = e.__class__.__name__
            error_message = f"Unexpected error: {str(e)}"
            print(f"[ERROR] Unexpected error: {error_message}")

        # Finalize result
        completed_at = datetime.utcnow()
        duration_seconds = (completed_at - started_at).total_seconds()

        if status == ExecutionStatus.FAILED:
            self._emit_event("failed", {
                "execution_id": execution_id,
                "underwriting_processor_id": underwriting_processor_id,
                "processor_name": self.PROCESSOR_NAME,
                "error_type": error_type,
                "error_phase": error_phase,
                "error_message": error_message,
            })

        return ProcessingResult(
            execution_id=execution_id,
            processor_name=self.PROCESSOR_NAME,
            underwriting_processor_id=underwriting_processor_id,
            status=status,
            started_at=started_at,
            completed_at=completed_at,
            duration_seconds=duration_seconds,
            output=output,
            total_cost_cents=self._total_cost,
            cost_breakdown=self._cost_breakdown,
            error_message=error_message,
            error_type=error_type,
            error_phase=error_phase,
            document_revision_ids=self._document_revision_ids,
            document_ids_hash=self._document_ids_hash,
        )
