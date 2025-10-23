"""
Test Stipulation Processor

A test implementation of a STIPULATION type processor for testing the BaseProcessor
framework and workflow orchestration.
"""

from typing import Any, Dict, List
from datetime import datetime, timezone
from ...base_processor import BaseProcessor
from ...models import ProcessorType, ValidationResult, ExecutionPayload


class TestStipulationProcessor(BaseProcessor):
    """
    Test Stipulation Processor - processes documents by stipulation type.

    This processor extracts factors from documents grouped by stipulation type
    and is used for testing the BaseProcessor framework and workflow orchestration.
    """

    # Required class constants
    PROCESSOR_NAME = "test_stipulation_processor"
    PROCESSOR_TYPE = ProcessorType.STIPULATION
    PROCESSOR_TRIGGERS = {"documents_list": ["s_drivers_license"]}
    CONFIG = {
        "processor_type": "STIPULATION",
        "test_mode": True,
        "debug_output": True,
        "mock_delay_ms": 1500,
        "stipulation_types": ["s_drivers_license"],
    }

    def transform_input(self, payload: ExecutionPayload) -> Dict[str, Any]:
        """
        Transform stipulation document data into standardized format.

        Args:
            payload: Raw execution payload

        Returns:
            Transformed stipulation data
        """
        # For stipulation processors, the payload should contain revision_ids
        revision_ids = payload.revision_ids or []
        return {
            "stipulation_type": "s_bank_statement",  # Default for test
            "revision_ids": revision_ids,
            "document_count": len(revision_ids),
        }

    def validate_input(self, transformed_data: Dict[str, Any]) -> ValidationResult:
        """
        Validate transformed stipulation data.

        Args:
            transformed_data: Transformed stipulation data

        Returns:
            Validation result with success status and any errors
        """
        errors = []

        if not transformed_data.get("stipulation_type"):
            errors.append("Stipulation type is required")

        if not transformed_data.get("revision_ids"):
            errors.append("At least one document revision is required")

        # Check if stipulation type is supported
        supported_types = [
            "s_bank_statement",
            "s_drivers_license",
        ]  # Default supported types
        if transformed_data.get("stipulation_type") not in supported_types:
            errors.append(
                f"Unsupported stipulation type: {transformed_data.get('stipulation_type')}"
            )

        return ValidationResult(is_valid=len(errors) == 0, errors=errors)

    def extract(self, validated_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract factors from validated stipulation data.

        Args:
            validated_data: Validated stipulation data

        Returns:
            Extracted factors and metadata
        """
        # Simulate processing delay
        import time

        time.sleep(self.CONFIG.get("mock_delay_ms", 1500) / 1000.0)

        stipulation_type = validated_data["stipulation_type"]
        revision_ids = validated_data["revision_ids"]
        document_count = validated_data["document_count"]

        # Extract stipulation-specific factors
        factors = {
            "f_stipulation_type": stipulation_type,
            "f_document_count": document_count,
            "f_revision_ids": revision_ids,
        }

        # Add stipulation-specific processing
        if stipulation_type == "s_bank_statement":
            factors.update(
                {
                    "f_bank_statement_count": document_count,
                    "f_bank_statement_processed": True,
                    "f_avg_monthly_revenue": 50000.0,  # Mock data
                    "f_nsf_count": 2,  # Mock data
                }
            )
        elif stipulation_type == "s_drivers_license":
            factors.update(
                {
                    "f_drivers_license_count": document_count,
                    "f_drivers_license_processed": True,
                    "f_identity_verified": True,  # Mock data
                    "f_license_valid": True,  # Mock data
                }
            )

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
                "stipulation_type": stipulation_type,
                "document_count": document_count,
                "extraction_method": "test_stipulation_extraction",
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
        supported_types = [
            "s_bank_statement",
            "s_drivers_license",
        ]  # Default supported types

        if stipulation_type not in supported_types:
            return False, f"Unsupported stipulation type: {stipulation_type}"

        # Check if documents are available
        revision_ids = payload.get("revision_id", [])
        if not revision_ids:
            return False, "No documents available for stipulation type"

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

        # For multiple stipulation executions, aggregate the results
        consolidated_factors = {}
        total_documents = 0

        for execution in executions:
            factors = execution.get("factors", {})
            total_documents += factors.get("f_document_count", 0)

            # Merge factors (latest values win for conflicts)
            consolidated_factors.update(factors)

        # Update aggregated values
        consolidated_factors["f_total_documents"] = total_documents
        consolidated_factors["f_execution_count"] = len(executions)

        return consolidated_factors
