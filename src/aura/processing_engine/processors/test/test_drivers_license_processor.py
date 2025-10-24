"""
Test Drivers License Processor

A test implementation of a DOCUMENT type processor for testing drivers license
document processing in the BaseProcessor framework and workflow orchestration.
"""

from typing import Any, Dict, List
from datetime import datetime, timezone
from ...base_processor import BaseProcessor
from ...models import ProcessorType, ValidationResult, ExecutionPayload


class TestDriversLicenseProcessor(BaseProcessor):
    """
    Test Drivers License Processor - processes drivers license documents.

    This processor extracts factors from individual drivers license documents
    and is used for testing the BaseProcessor framework and workflow orchestration.
    """

    # Required class constants
    PROCESSOR_NAME = "test_drivers_license_processor"
    PROCESSOR_TYPE = ProcessorType.DOCUMENT
    PROCESSOR_TRIGGERS = {"documents_list": ["s_drivers_license"]}
    CONFIG = {
        "processor_type": "DOCUMENT",
        "test_mode": True,
        "debug_output": True,
        "mock_delay_ms": 1500,
        "stipulation_types": ["s_drivers_license"],
    }

    def transform_input(self, payload: ExecutionPayload) -> Dict[str, Any]:
        """
        Transform drivers license document data into standardized format.

        Args:
            payload: Raw execution payload

        Returns:
            Transformed drivers license data
        """
        # For document processors, the payload should contain a single revision_id
        revision_id = payload.revision_id
        return {
            "stipulation_type": "s_drivers_license",
            "revision_id": revision_id,
            "document_type": "drivers_license",
        }

    def validate_input(self, transformed_data: Dict[str, Any]) -> ValidationResult:
        """
        Validate transformed drivers license data.

        Args:
            transformed_data: Transformed drivers license data

        Returns:
            Validation result with success status and any errors
        """
        errors = []

        if not transformed_data.get("revision_id"):
            errors.append("Document revision ID is required")

        if not transformed_data.get("stipulation_type"):
            errors.append("Stipulation type is required")

        # Check if stipulation type is supported
        stipulation_type = transformed_data.get("stipulation_type")
        if stipulation_type != "s_drivers_license":
            errors.append(f"Unsupported stipulation type: {stipulation_type}")

        return ValidationResult(is_valid=len(errors) == 0, errors=errors)

    def extract(self, validated_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract factors from validated drivers license data.

        Args:
            validated_data: Validated drivers license data

        Returns:
            Extracted factors and metadata
        """
        # Simulate processing delay
        import time

        time.sleep(self.CONFIG.get("mock_delay_ms", 1500) / 1000.0)

        revision_id = validated_data["revision_id"]

        # Extract drivers license-specific factors
        factors = {
            "f_stipulation_type": "s_drivers_license",
            "f_revision_id": revision_id,
            "f_drivers_license_processed": True,
            "f_identity_verified": True,  # Mock data
            "f_license_valid": True,  # Mock data
            "f_license_number": "DL123456789",  # Mock data
            "f_license_state": "CA",  # Mock data
            "f_license_expiry": "2025-12-31",  # Mock data
        }

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
                "stipulation_type": "s_drivers_license",
                "revision_id": revision_id,
                "extraction_method": "test_drivers_license_extraction",
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

        if not factors.get("f_identity_verified"):
            errors.append("Missing identity verification factor")

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
        if stipulation_type != "s_drivers_license":
            return False, f"Unsupported stipulation type: {stipulation_type}"

        # Check if document is available
        revision_id = payload.get("revision_id")
        if not revision_id:
            return False, "No drivers license document available"

        return True, None

    @staticmethod
    def consolidate(factors_delta_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Consolidate multiple execution results.

        Args:
            factors_delta_list: List of factors_delta dictionaries from executions

        Returns:
            Consolidated factors
        """
        if not factors_delta_list:
            return {}

        if len(factors_delta_list) == 1:
            return factors_delta_list[0]

        # For multiple drivers license executions, use the latest one
        # (document processors typically process one document at a time)
        return factors_delta_list[-1]

