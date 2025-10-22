"""
Test Application Processor

Demonstrates APPLICATION type processor that processes application form data.
Validates business information and extracts basic factors.
"""

from typing import Any
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent / "src"))

from aura.processing_engine.base_processor import BaseProcessor
from aura.processing_engine.models import ProcessorType, ExecutionPayload, ValidationResult


class ApplicationProcessor(BaseProcessor):
    """
    Test processor for APPLICATION type.

    Processes application form data to validate and extract business info.
    This type processes form data, not documents.
    """

    # Required configuration
    PROCESSOR_NAME: str = "p_test_application"
    PROCESSOR_TYPE: ProcessorType = ProcessorType.APPLICATION
    PROCESSOR_TRIGGERS: dict[str, list[str]] = {
        "application_form": ["merchant.name", "merchant.ein"]
    }
    CONFIG: dict[str, Any] = {
        "require_ein": True,
        "require_industry": True,
    }

    def transform_input(self, payload: ExecutionPayload) -> dict[str, Any]:
        """
        Transform application form data into structured format.
        """
        app_form = payload.application_form

        # Extract and structure merchant info
        transformed = {
            "merchant_name": app_form.get("merchant.name"),
            "merchant_ein": app_form.get("merchant.ein"),
            "merchant_industry": app_form.get("merchant.industry"),
            "merchant_state": app_form.get("merchant.state_of_incorporation"),
            "merchant_entity_type": app_form.get("merchant.entity_type"),
            "owners": payload.owners_list,
            "config": payload.config,
        }

        return transformed

    def validate_input(self, transformed_data: dict[str, Any]) -> ValidationResult:
        """
        Validate transformed application data.
        """
        result = ValidationResult(is_valid=True)
        config = transformed_data.get("config", {})

        # Check required fields based on config
        if config.get("require_ein", True):
            if not transformed_data.get("merchant_ein"):
                result.add_error("Merchant EIN is required")

        if config.get("require_industry", True):
            if not transformed_data.get("merchant_industry"):
                result.add_error("Merchant industry is required")

        # Check merchant name
        if not transformed_data.get("merchant_name"):
            result.add_error("Merchant name is required")

        # Validate owners
        owners = transformed_data.get("owners", [])
        if not owners:
            result.add_warning("No owners provided")

        return result

    def extract(self, validated_data: dict[str, Any]) -> dict[str, Any]:
        """
        Extract factors from application form data.
        """
        # Extract basic business information
        output = {
            "business_name": validated_data.get("merchant_name"),
            "business_ein": validated_data.get("merchant_ein"),
            "business_industry": validated_data.get("merchant_industry"),
            "business_state": validated_data.get("merchant_state"),
            "business_entity_type": validated_data.get("merchant_entity_type"),
            "owner_count": len(validated_data.get("owners", [])),
            "has_primary_owner": any(
                owner.get("primary_owner", False)
                for owner in validated_data.get("owners", [])
            ),
        }

        # Add cost for application processing
        self._add_cost(1.0, "application_processing")

        return output

    def validate_output(self, output: dict[str, Any]) -> ValidationResult:
        """
        Validate extraction output.
        """
        result = ValidationResult(is_valid=True)

        # Check required output fields
        if not output.get("business_name"):
            result.add_error("Business name not extracted")

        if not output.get("business_ein"):
            result.add_error("Business EIN not extracted")

        # Validate owner count
        owner_count = output.get("owner_count", 0)
        if owner_count == 0:
            result.add_warning("No owners found")
        elif owner_count > 5:
            result.add_warning(f"Unusually high owner count: {owner_count}")

        return result

