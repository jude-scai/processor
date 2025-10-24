"""
Test Bank Statement Processor

A test implementation of a STIPULATION type processor for testing bank statement
processing in the BaseProcessor framework and workflow orchestration.
"""

from typing import Any, Dict, List
from datetime import datetime, timezone
from ...base_processor import BaseProcessor
from ...models import ProcessorType, ValidationResult, ExecutionPayload


class TestBankStatementProcessor(BaseProcessor):
    """
    Test Bank Statement Processor - processes bank statement documents.

    This processor extracts factors from bank statement documents grouped by
    stipulation type and is used for testing the BaseProcessor framework and
    workflow orchestration.
    """

    # Required class constants
    PROCESSOR_NAME = "test_bank_statement_processor"
    PROCESSOR_TYPE = ProcessorType.STIPULATION
    PROCESSOR_TRIGGERS = {"documents_list": ["s_bank_statement"]}
    CONFIG = {
        "processor_type": "STIPULATION",
        "test_mode": True,
        "debug_output": True,
        "mock_delay_ms": 2000,
        "stipulation_types": ["s_bank_statement"],
        "minimum_document": 3,
    }

    def transform_input(self, payload: ExecutionPayload) -> Dict[str, Any]:
        """
        Transform bank statement document data into standardized format.

        Args:
            payload: Raw execution payload

        Returns:
            Transformed bank statement data
        """
        # For stipulation processors, the payload should contain revision_ids
        revision_ids = payload.revision_ids or []
        return {
            "stipulation_type": "s_bank_statement",
            "revision_ids": revision_ids,
            "document_count": len(revision_ids),
        }

    def validate_input(self, transformed_data: Dict[str, Any]) -> ValidationResult:
        """
        Validate transformed bank statement data.

        Args:
            transformed_data: Transformed bank statement data

        Returns:
            Validation result with success status and any errors
        """
        errors = []

        if not transformed_data.get("stipulation_type"):
            errors.append("Stipulation type is required")

        if not transformed_data.get("revision_ids"):
            errors.append("At least one document revision is required")

        # Check minimum document requirement
        document_count = transformed_data.get("document_count", 0)
        minimum_document = self.CONFIG.get("minimum_document", 3)
        if document_count < minimum_document:
            errors.append(
                f"Minimum {minimum_document} bank statements required, got {document_count}"
            )

        return ValidationResult(is_valid=len(errors) == 0, errors=errors)

    def extract(self, validated_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract factors from validated bank statement data.

        Args:
            validated_data: Validated bank statement data

        Returns:
            Extracted factors and metadata
        """
        # Simulate processing delay
        import time

        time.sleep(self.CONFIG.get("mock_delay_ms", 2000) / 1000.0)

        revision_ids = validated_data["revision_ids"]
        document_count = validated_data["document_count"]

        # Extract bank statement-specific factors
        factors = {
            "f_stipulation_type": "s_bank_statement",
            "f_document_count": document_count,
            "f_revision_ids": revision_ids,
            "f_bank_statement_count": document_count,
            "f_bank_statement_processed": True,
            "f_avg_monthly_revenue": 50000.0,  # Mock data
            "f_nsf_count": 2,  # Mock data
            "f_cash_flow_positive": True,  # Mock data
            "f_minimum_balance": 10000.0,  # Mock data
        }

        # Add test-specific factors
        factors.update(
            {
                "f_test_processor_type": "STIPULATION",
                "f_test_mode": True,
                "f_extraction_timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )

        return {
            "factors": factors,
            "metadata": {
                "processor_name": self.PROCESSOR_NAME,
                "processor_type": self.PROCESSOR_TYPE.value,
                "stipulation_type": "s_bank_statement",
                "document_count": document_count,
                "extraction_method": "test_bank_statement_extraction",
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
        if not factors.get("f_stipulation_type"):
            errors.append("Missing stipulation type factor")

        if not factors.get("f_document_count"):
            errors.append("Missing document count factor")

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
        # Check if stipulation type is supported
        stipulation_type = payload.get("stipulation_type")
        if stipulation_type != "s_bank_statement":
            return False, f"Unsupported stipulation type: {stipulation_type}"

        # Check if documents are available
        revision_ids = payload.get("revision_id", [])
        if not revision_ids:
            return False, "No bank statement documents available"

        # Check minimum document requirement
        document_count = len(revision_ids)
        minimum_document = 3  # From CONFIG
        if document_count < minimum_document:
            return (
                False,
                f"Minimum {minimum_document} bank statements required, got {document_count}",
            )

        return True, None
