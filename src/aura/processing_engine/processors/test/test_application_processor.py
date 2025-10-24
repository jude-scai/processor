"""
Test Application Processor

A test implementation of an APPLICATION type processor for testing the BaseProcessor
framework and workflow orchestration.
"""

from typing import Any, Dict, List
from datetime import datetime, timezone
from ...base_processor import BaseProcessor
from ...models import ProcessorType, ValidationResult, ExecutionPayload


class TestApplicationProcessor(BaseProcessor):
    """
    Test Application Processor - processes application form data.

    This processor extracts factors from application form data and is used for
    testing the BaseProcessor framework and workflow orchestration.
    """

    # Required class constants
    PROCESSOR_NAME = "test_application_processor"
    PROCESSOR_TYPE = ProcessorType.APPLICATION
    PROCESSOR_TRIGGERS = {
        "application_form": ["merchant.name", "merchant.ein", "merchant.industry"]
    }
    CONFIG = {
        "processor_type": "APPLICATION",
        "test_mode": True,
        "debug_output": True,
        "mock_delay_ms": 1000,
    }

    def transform_input(self, payload: ExecutionPayload) -> Dict[str, Any]:
        """
        Transform application form data into standardized format.

        Args:
            payload: Raw execution payload

        Returns:
            Transformed application data
        """
        # Extract application form data from payload
        application_form = payload.application_form

        return {
            "merchant_name": application_form.get("merchant.name"),
            "merchant_ein": application_form.get("merchant.ein"),
            "merchant_industry": application_form.get("merchant.industry"),
            "request_amount": application_form.get("request_amount"),
            "purpose": application_form.get("purpose"),
        }

    def validate_input(self, transformed_data: Dict[str, Any]) -> ValidationResult:
        """
        Validate transformed application data.

        Args:
            transformed_data: Transformed application data

        Returns:
            Validation result with success status and any errors
        """
        errors = []

        if not transformed_data.get("merchant_name"):
            errors.append("Merchant name is required")

        if not transformed_data.get("merchant_ein"):
            errors.append("Merchant EIN is required")

        if not transformed_data.get("merchant_industry"):
            errors.append("Merchant industry is required")

        return ValidationResult(is_valid=len(errors) == 0, errors=errors)

    def extract(self, validated_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract factors from validated application data.

        Args:
            validated_data: Validated application data

        Returns:
            Extracted factors and metadata
        """
        # Simulate processing delay
        import time

        time.sleep(self.CONFIG.get("mock_delay_ms", 1000) / 1000.0)

        # Extract basic factors
        factors = {
            "f_merchant_name": validated_data["merchant_name"],
            "f_merchant_ein": validated_data["merchant_ein"],
            "f_merchant_industry": validated_data["merchant_industry"],
            "f_request_amount": validated_data.get("request_amount", 0),
            "f_purpose": validated_data.get("purpose", ""),
        }

        # Add test-specific factors
        factors.update(
            {
                "f_test_processor_type": "APPLICATION",
                "f_test_mode": True,
                "f_extraction_timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )

        return {
            "factors": factors,
            "metadata": {
                "processor_name": self.PROCESSOR_NAME,
                "processor_type": self.PROCESSOR_TYPE.value,
                "extraction_method": "test_application_extraction",
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
        if not factors.get("f_merchant_name"):
            errors.append("Missing merchant name factor")

        if not factors.get("f_merchant_ein"):
            errors.append("Missing merchant EIN factor")

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
        # Check if required application form fields are present
        required_fields = ["merchant.name", "merchant.ein", "merchant.industry"]
        missing_fields = [
            field
            for field in required_fields
            if not payload.application_form.get(field)
        ]

        if missing_fields:
            return False, f"Missing required fields: {', '.join(missing_fields)}"

        return True, None

