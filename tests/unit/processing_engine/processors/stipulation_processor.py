"""
Test Stipulation Processor

Demonstrates STIPULATION type processor that processes multiple documents
of the same type together (e.g., all bank statements for revenue analysis).
"""

from typing import Any

from src.aura.processing_engine.base_processor import BaseProcessor
from src.aura.processing_engine.models import ProcessorType, ExecutionPayload, ValidationResult


class StipulationProcessor(BaseProcessor):
    """
    Test processor for STIPULATION type.

    Processes all documents of a specific stipulation type together.
    Example: Analyzing multiple bank statements to calculate average revenue.
    """

    # Required configuration
    PROCESSOR_NAME: str = "p_test_stipulation"
    PROCESSOR_TYPE: ProcessorType = ProcessorType.STIPULATION
    PROCESSOR_TRIGGERS: dict[str, list[str]] = {
        "documents_list": ["s_bank_statement"]
    }
    CONFIG: dict[str, Any] = {
        "minimum_document": 3,
        "analysis_window_months": 6,
    }

    @staticmethod
    def should_execute(payload: dict[str, Any]) -> tuple[bool, str | None]:
        """
        Check if minimum document requirement is met.
        """
        documents = payload.get("documents_list", [])
        bank_statements = [
            doc for doc in documents
            if doc.get("stipulation_type") == "s_bank_statement"
        ]

        min_required = payload.get("config", {}).get("minimum_document", 3)
        if len(bank_statements) < min_required:
            return False, f"Requires minimum {min_required} bank statements"

        return True, None

    def transform_input(self, payload: ExecutionPayload) -> dict[str, Any]:
        """
        Transform payload by extracting all bank statement documents.
        """
        # Filter bank statement documents
        bank_statements = [
            doc for doc in payload.documents_list
            if doc.get("stipulation_type") == "s_bank_statement"
        ]

        # Track all document revisions
        for doc in bank_statements:
            if "revision_id" in doc:
                self._add_document_revision_id(doc["revision_id"])

        # Track base document IDs for hash
        document_ids = [
            doc.get("document_id", doc.get("revision_id"))
            for doc in bank_statements
        ]
        self._set_document_ids_hash(document_ids)

        transformed = {
            "documents": bank_statements,
            "document_count": len(bank_statements),
            "config": payload.config,
        }

        return transformed

    def validate_input(self, transformed_data: dict[str, Any]) -> ValidationResult:
        """
        Validate transformed document data.
        """
        result = ValidationResult(is_valid=True)
        config = transformed_data.get("config", {})

        # Check minimum document count
        doc_count = transformed_data.get("document_count", 0)
        min_required = config.get("minimum_document", 3)

        if doc_count < min_required:
            result.add_error(
                f"Insufficient documents: {doc_count} < {min_required} required"
            )

        # Validate each document structure
        for i, doc in enumerate(transformed_data.get("documents", [])):
            if "revision_id" not in doc:
                result.add_error(f"Document {i} missing revision_id")
            if "uri" not in doc:
                result.add_error(f"Document {i} missing uri")

        return result

    def extract(self, validated_data: dict[str, Any]) -> dict[str, Any]:
        """
        Extract revenue factors from all bank statements.

        In real implementation, would download PDFs, parse transactions,
        and calculate actual revenue figures.
        """
        documents = validated_data.get("documents", [])
        config = validated_data.get("config", {})

        # Simulate processing each document
        monthly_revenues = []
        for _doc in documents:
            # In real implementation:
            # - Download document from GCS
            # - Parse PDF
            # - Extract transactions
            # - Calculate monthly revenue

            # Mock data for testing
            monthly_revenue = 45000.0
            monthly_revenues.append(monthly_revenue)

            # Track cost per document
            self._add_cost(2.0, "document_processing")

        # Calculate aggregate metrics
        if monthly_revenues:
            avg_revenue = sum(monthly_revenues) / len(monthly_revenues)
            min_revenue = min(monthly_revenues)
            max_revenue = max(monthly_revenues)
        else:
            avg_revenue = min_revenue = max_revenue = 0.0

        output = {
            "monthly_revenues": monthly_revenues,
            "avg_monthly_revenue": avg_revenue,
            "min_monthly_revenue": min_revenue,
            "max_monthly_revenue": max_revenue,
            "months_analyzed": len(documents),
            "analysis_window": config.get("analysis_window_months", 6),
        }

        return output

    def validate_output(self, output: dict[str, Any]) -> ValidationResult:
        """
        Validate extraction output.
        """
        result = ValidationResult(is_valid=True)

        # Check required fields
        required_fields = ["monthly_revenues", "avg_monthly_revenue", "months_analyzed"]
        for field in required_fields:
            if field not in output:
                result.add_error(f"Missing required field: {field}")

        # Validate values
        if output.get("avg_monthly_revenue", 0) < 0:
            result.add_error("Average monthly revenue cannot be negative")

        if output.get("months_analyzed", 0) < 1:
            result.add_error("Must analyze at least 1 month")

        return result

    @staticmethod
    def consolidate(executions: list[Any]) -> dict[str, Any]:
        """
        Consolidate multiple executions into final factors.

        For stipulation processors, we might have multiple executions
        (e.g., different sets of months). Consolidate across all.
        """
        if not executions:
            return {}

        # Aggregate all monthly revenues across executions
        all_monthly_revenues = []
        total_months = 0

        for execution in executions:
            output = getattr(execution, "output", execution)
            if isinstance(output, dict):
                revenues = output.get("monthly_revenues", [])
                all_monthly_revenues.extend(revenues)
                total_months += output.get("months_analyzed", 0)

        # Calculate consolidated factors
        if all_monthly_revenues:
            avg_revenue = sum(all_monthly_revenues) / len(all_monthly_revenues)
            min_revenue = min(all_monthly_revenues)
            max_revenue = max(all_monthly_revenues)
        else:
            avg_revenue = min_revenue = max_revenue = 0.0

        # Return consolidated factors with f_ prefix
        return {
            "f_revenue_monthly_avg": avg_revenue,
            "f_revenue_monthly_min": min_revenue,
            "f_revenue_monthly_max": max_revenue,
            "f_total_months_analyzed": total_months,
        }

