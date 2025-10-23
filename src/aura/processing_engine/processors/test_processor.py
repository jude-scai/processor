"""
Test Application Processor

Simple test processor for API testing and demonstrations.
Processes application form data and extracts basic merchant information.
"""

from typing import Any

from ..base_processor import BaseProcessor
from ..models import ProcessorType, ExecutionPayload, ValidationResult


class TestApplicationProcessor(BaseProcessor):
    """
    Test processor for APPLICATION type.

    Processes application form data to validate and extract business info.
    This type processes form data, not documents.
    """

    # Required configuration
    PROCESSOR_NAME: str = "p_application"
    PROCESSOR_TYPE: ProcessorType = ProcessorType.APPLICATION
    PROCESSOR_TRIGGERS: dict[str, list[str]] = {
        "application_form": ["merchant.name", "merchant.ein"]
    }
    CONFIG: dict[str, Any] = {
        "require_ein": True,
        "require_industry": False,
    }

    def transform_input(self, payload: ExecutionPayload) -> dict[str, Any]:
        """
        Transform application form data into structured format.
        
        Args:
            payload: Raw execution payload with application form
            
        Returns:
            Transformed data dictionary
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
        }

        return transformed

    def validate_input(self, transformed_data: dict[str, Any]) -> ValidationResult:
        """
        Validate transformed input data.
        
        Args:
            transformed_data: Output from transform_input()
            
        Returns:
            ValidationResult indicating if input is valid
        """
        errors = []

        # Check required fields
        if not transformed_data.get("merchant_name"):
            errors.append("merchant_name is required")

        # Get config if repository is available, otherwise use defaults
        try:
            config = self.get_config()
        except ValueError:
            # Repository not initialized, use default config
            config = self.CONFIG
        
        if config.get("require_ein") and not transformed_data.get("merchant_ein"):
            errors.append("merchant_ein is required when require_ein=True")

        if errors:
            return ValidationResult(is_valid=False, errors=errors)

        return ValidationResult(is_valid=True, errors=[])

    def extract(self, validated_data: dict[str, Any]) -> dict[str, Any]:
        """
        Extract factors from validated input data.
        
        Args:
            validated_data: Validated input data
            
        Returns:
            Dictionary of extracted factors
        """
        # Extract basic merchant information
        output = {
            "f_merchant_name": validated_data.get("merchant_name"),
            "f_merchant_ein": validated_data.get("merchant_ein"),
            "f_merchant_industry": validated_data.get("merchant_industry"),
            "f_merchant_state": validated_data.get("merchant_state"),
            "f_merchant_entity_type": validated_data.get("merchant_entity_type"),
            "f_owner_count": len(validated_data.get("owners", [])),
        }

        # Add primary owner info if available
        owners = validated_data.get("owners", [])
        primary_owner = next(
            (o for o in owners if o.get("primary_owner")), 
            owners[0] if owners else None
        )
        
        if primary_owner:
            output["f_primary_owner_name"] = f"{primary_owner.get('first_name', '')} {primary_owner.get('last_name', '')}".strip()

        # Track some cost (example: $0.10 per execution)
        self._add_cost(10, "api_call")

        return output

    def validate_output(self, output: dict[str, Any]) -> ValidationResult:
        """
        Validate extraction output.
        
        Args:
            output: Output from extract()
            
        Returns:
            ValidationResult indicating if output is valid
        """
        errors = []

        # Basic output validation
        if not output.get("f_merchant_name"):
            errors.append("f_merchant_name must be present in output")

        if errors:
            return ValidationResult(is_valid=False, errors=errors)

        return ValidationResult(is_valid=True, errors=[])

    @staticmethod
    def consolidate(executions: list[Any]) -> dict[str, Any]:
        """
        Consolidate multiple execution outputs into final factors.
        
        For APPLICATION processors, typically only one execution exists,
        so we return the latest execution's output.
        
        Args:
            executions: List of active execution records
            
        Returns:
            Consolidated factors dictionary
        """
        if not executions:
            return {}
        
        # For application processors, use the most recent execution
        latest = executions[-1]
        return latest.get('output', {}) if isinstance(latest, dict) else (latest.output or {})

