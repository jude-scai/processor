"""
Test Application 2 Processor

A second application-based processor for testing purposes.
This processor extracts different fields than the first test application processor.
"""

from typing import Any
from ...base_processor import BaseProcessor, ProcessorType
from ...models import ExecutionPayload, ProcessingResult, ValidationResult


class TestApplication2Processor(BaseProcessor):
    """
    Test application processor that extracts industry and entity type information.
    """

    PROCESSOR_NAME = "p_test_application_2"
    PROCESSOR_TYPE = ProcessorType.APPLICATION
    PROCESSOR_TRIGGERS = {"application_form": [""]}

    def transform_input(self, payload: ExecutionPayload) -> dict[str, Any]:
        """
        Transform input payload into format needed for extraction.

        Args:
            payload: Execution payload with application form data

        Returns:
            Transformed data dictionary
        """
        application_form = payload.application_form

        return {
            "merchant_industry": application_form.get("merchant.industry"),
            "merchant_entity_type": application_form.get("merchant.entity_type"),
            "merchant_name": application_form.get("merchant.name"),
            "merchant_ein": application_form.get("merchant.ein"),
        }

    def validate_input(self, transformed_data: dict[str, Any]) -> ValidationResult:
        """
        Validate transformed input data.

        Args:
            transformed_data: Transformed data from transform_input

        Returns:
            ValidationResult with success status and any error messages
        """
        # Check for required fields
        required_fields = ["merchant_industry", "merchant_entity_type"]
        missing_fields = [
            field for field in required_fields if not transformed_data.get(field)
        ]

        if missing_fields:
            result = ValidationResult(is_valid=False)
            result.add_error(f"Missing required fields: {', '.join(missing_fields)}")
            return result

        return ValidationResult(is_valid=True)

    def extract(self, validated_data: dict[str, Any]) -> dict[str, Any]:
        """
        Extract factors from validated data.

        Args:
            validated_data: Validated data from validate_input

        Returns:
            Dictionary of extracted factors
        """
        # Extract industry information
        industry = validated_data.get("merchant_industry")
        entity_type = validated_data.get("merchant_entity_type")

        # Simulate some basic industry analysis
        high_risk_industries = ["1234", "5678", "9012"]  # Example industry codes
        is_high_risk = industry in high_risk_industries

        return {
            "f_merchant_industry": industry,
            "f_merchant_entity_type": entity_type,
            "f_merchant_industry_risk": "high" if is_high_risk else "low",
            "f_merchant_name": validated_data.get("merchant_name"),
            "f_merchant_ein": validated_data.get("merchant_ein"),
        }

    def validate_output(self, extraction_output: dict[str, Any]) -> ValidationResult:
        """
        Validate extraction output.

        Args:
            extraction_output: Output from extract method

        Returns:
            ValidationResult with success status and any error messages
        """
        # Check that required factors were extracted
        required_factors = ["f_merchant_industry", "f_merchant_entity_type"]
        missing_factors = [
            factor for factor in required_factors if factor not in extraction_output
        ]

        if missing_factors:
            result = ValidationResult(is_valid=False)
            result.add_error(f"Missing required factors: {', '.join(missing_factors)}")
            return result

        return ValidationResult(is_valid=True)

    @staticmethod
    def should_execute(payload: ExecutionPayload) -> ValidationResult:
        """
        Determine if processor should execute based on payload.

        Args:
            payload: Execution payload

        Returns:
            ValidationResult indicating whether to execute
        """
        # Check if required fields are present
        required_fields = ["merchant.industry", "merchant.entity_type"]
        missing_fields = [
            field
            for field in required_fields
            if not payload.application_form.get(field)
        ]

        if missing_fields:
            result = ValidationResult(is_valid=False)
            result.add_error(
                f"Required fields not available: {', '.join(missing_fields)}"
            )
            return result

        return ValidationResult(is_valid=True)
