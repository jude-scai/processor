"""
Test Document Processor

A test implementation of a DOCUMENT type processor for testing the BaseProcessor
framework and workflow orchestration.
"""

from typing import Any, Dict, List
from datetime import datetime, timezone
from ...base_processor import BaseProcessor
from ...models import ProcessorType, ValidationResult, ExecutionPayload


class TestDocumentProcessor(BaseProcessor):
    """
    Test Document Processor - processes individual documents.

    This processor extracts factors from individual document revisions
    and is used for testing the BaseProcessor framework and workflow orchestration.
    """

    # Required class constants
    PROCESSOR_NAME = "test_document_processor"
    PROCESSOR_TYPE = ProcessorType.DOCUMENT
    PROCESSOR_TRIGGERS = {
        "documents_list": [
            "s_bank_statement",
            "s_drivers_license",
            "s_business_registration",
        ]
    }
    CONFIG = {
        "processor_type": "DOCUMENT",
        "test_mode": True,
        "debug_output": True,
        "mock_delay_ms": 2000,
        "document_types": ["application/pdf", "image/png", "image/jpeg"],
    }

    def transform_input(self, payload: ExecutionPayload) -> Dict[str, Any]:
        """
        Transform document data into standardized format.

        Args:
            payload: Raw execution payload

        Returns:
            Transformed document data
        """
        # For document processors, the payload should contain document metadata
        # Note: Document processors receive revision_id in the payload
        return {
            "revision_id": getattr(payload, "revision_id", None),
            "document_id": getattr(payload, "document_id", None),
            "stipulation_type": getattr(payload, "stipulation_type", None),
            "filename": getattr(payload, "filename", None),
            "mime_type": getattr(payload, "mime_type", None),
        }

    def validate_input(self, transformed_data: Dict[str, Any]) -> ValidationResult:
        """
        Validate transformed document data.

        Args:
            transformed_data: Transformed document data

        Returns:
            Validation result with success status and any errors
        """
        errors = []

        if not transformed_data.get("revision_id"):
            errors.append("Document revision ID is required")

        # For test purposes, use revision_id as document_id if not provided
        if not transformed_data.get("document_id"):
            transformed_data["document_id"] = transformed_data.get(
                "revision_id", "test_doc_id"
            )

        # For test purposes, use a default stipulation type if not provided
        if not transformed_data.get("stipulation_type"):
            transformed_data["stipulation_type"] = "s_bank_statement"

        # Check if document type is supported
        mime_type = transformed_data.get("mime_type")
        supported_types = self.CONFIG.get("document_types", [])
        if mime_type and mime_type not in supported_types:
            errors.append(f"Unsupported document type: {mime_type}")

        return ValidationResult(is_valid=len(errors) == 0, errors=errors)

    def extract(self, validated_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract factors from validated document data.

        Args:
            validated_data: Validated document data

        Returns:
            Extracted factors and metadata
        """
        # Simulate processing delay
        import time

        time.sleep(self.CONFIG.get("mock_delay_ms", 2000) / 1000.0)

        revision_id = validated_data["revision_id"]
        document_id = validated_data["document_id"]
        stipulation_type = validated_data["stipulation_type"]
        filename = validated_data.get("filename", "")
        mime_type = validated_data.get("mime_type", "")

        # Extract document-specific factors
        factors = {
            "f_revision_id": revision_id,
            "f_document_id": document_id,
            "f_stipulation_type": stipulation_type,
            "f_filename": filename,
            "f_mime_type": mime_type,
        }

        # Add document-specific processing based on stipulation type
        if stipulation_type == "s_bank_statement":
            factors.update(
                {
                    "f_bank_statement_processed": True,
                    "f_page_count": 3,  # Mock data
                    "f_ocr_confidence": 0.95,  # Mock data
                    "f_contains_transactions": True,  # Mock data
                }
            )
        elif stipulation_type == "s_drivers_license":
            factors.update(
                {
                    "f_drivers_license_processed": True,
                    "f_license_number": "D123456789",  # Mock data
                    "f_expiration_date": "2025-12-31",  # Mock data
                    "f_state": "CA",  # Mock data
                }
            )
        elif stipulation_type == "s_business_registration":
            factors.update(
                {
                    "f_business_registration_processed": True,
                    "f_registration_number": "REG123456",  # Mock data
                    "f_entity_type": "LLC",  # Mock data
                    "f_registration_date": "2020-01-15",  # Mock data
                }
            )

        # Add test-specific factors
        factors.update(
            {
                "f_test_processor_type": "DOCUMENT",
                "f_test_mode": True,
                "f_extraction_timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )

        return {
            "factors": factors,
            "metadata": {
                "processor_name": self.PROCESSOR_NAME,
                "processor_type": self.PROCESSOR_TYPE.value,
                "revision_id": revision_id,
                "document_id": document_id,
                "stipulation_type": stipulation_type,
                "extraction_method": "test_document_extraction",
                "debug_output": self.CONFIG.get("debug_output", False),
            },
        }

    def validate_output(self, extraction_result: Dict[str, Any]) -> ValidationResult:
        """
        Validate extraction output.

        Args:
            extraction_result: Result from extract() method

        Returns:
            Validation result
        """
        errors = []

        if "factors" not in extraction_result:
            errors.append("Missing factors in extraction result")

        if "metadata" not in extraction_result:
            errors.append("Missing metadata in extraction result")

        factors = extraction_result.get("factors", {})
        if not factors.get("f_revision_id"):
            errors.append("Missing revision ID factor")

        if not factors.get("f_document_id"):
            errors.append("Missing document ID factor")

        if not factors.get("f_stipulation_type"):
            errors.append("Missing stipulation type factor")

        return ValidationResult(is_valid=len(errors) == 0, errors=errors)

    @staticmethod
    def should_execute(payload: Dict[str, Any]) -> tuple[bool, str | None]:
        """
        Determine if processor should execute based on payload.

        Args:
            payload: Input payload to evaluate

        Returns:
            Tuple of (should_execute, reason)
        """
        # Check if required document fields are present
        if not payload.get("revision_id"):
            return False, "Missing document revision ID"

        if not payload.get("document_id"):
            return False, "Missing document ID"

        # Check if stipulation type is supported
        stipulation_type = payload.get("stipulation_type")
        supported_types = [
            "s_bank_statement",
            "s_drivers_license",
            "s_business_registration",
        ]
        if stipulation_type not in supported_types:
            return False, f"Unsupported stipulation type: {stipulation_type}"

        return True, None

    @staticmethod
    def consolidate(executions: List[Any]) -> Dict[str, Any]:
        """
        Consolidate multiple execution results.

        Args:
            executions: List of execution results to consolidate

        Returns:
            Consolidated factors
        """
        if not executions:
            return {}

        if len(executions) == 1:
            return executions[0].get("factors", {})

        # For multiple document executions, collect all factors
        consolidated_factors = {}
        processed_documents = []

        for execution in executions:
            factors = execution.get("factors", {})
            processed_documents.append(
                {
                    "revision_id": factors.get("f_revision_id"),
                    "document_id": factors.get("f_document_id"),
                    "stipulation_type": factors.get("f_stipulation_type"),
                }
            )

            # Merge factors (latest values win for conflicts)
            consolidated_factors.update(factors)

        # Add aggregated metadata
        consolidated_factors["f_processed_documents"] = processed_documents
        consolidated_factors["f_total_documents_processed"] = len(executions)

        return consolidated_factors
