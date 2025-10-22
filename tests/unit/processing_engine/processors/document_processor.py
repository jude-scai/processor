"""
Test Document Processor

Demonstrates DOCUMENT type processor that processes each document individually.
Example: Driver's license verification where each license is processed separately.
"""

from typing import Any

from src.aura.processing_engine.base_processor import BaseProcessor
from src.aura.processing_engine.models import ProcessorType, ExecutionPayload, ValidationResult


class DocumentProcessor(BaseProcessor):
    """
    Test processor for DOCUMENT type.

    Processes each document individually (one execution per document).
    Example: Verifying individual driver's licenses, voided checks, etc.
    """

    # Required configuration
    PROCESSOR_NAME: str = "p_test_document"
    PROCESSOR_TYPE: ProcessorType = ProcessorType.DOCUMENT
    PROCESSOR_TRIGGERS: dict[str, list[str]] = {
        "documents_list": ["s_drivers_license"]
    }
    CONFIG: dict[str, Any] = {
        "require_photo": True,
        "check_expiration": True,
    }

    def transform_input(self, payload: ExecutionPayload) -> dict[str, Any]:
        """
        Transform payload for single document processing.

        For DOCUMENT type, each execution processes ONE document.
        The orchestrator creates separate executions for each document.
        """
        # Extract the specific driver's license document for this execution
        # In a real scenario, payload would contain a single document
        documents = [
            doc for doc in payload.documents_list
            if doc.get("stipulation_type") == "s_drivers_license"
        ]

        if not documents:
            # This should not happen if orchestrator filters correctly
            raise ValueError("No driver's license document found in payload")

        # For DOCUMENT type, we expect one document per execution
        # but let's handle the first one for this test
        document = documents[0]

        # Track document revision
        if "revision_id" in document:
            self._add_document_revision_id(document["revision_id"])

        # Track document ID for hash
        document_id = document.get("document_id", document.get("revision_id"))
        if document_id:
            self._set_document_ids_hash([document_id])

        transformed = {
            "document": document,
            "revision_id": document.get("revision_id"),
            "uri": document.get("uri"),
            "config": payload.config,
        }

        return transformed

    def validate_input(self, transformed_data: dict[str, Any]) -> ValidationResult:
        """
        Validate the document data.
        """
        result = ValidationResult(is_valid=True)

        # Check document structure
        document = transformed_data.get("document")
        if not document:
            result.add_error("No document provided")
            return result

        # Check required fields
        if not transformed_data.get("revision_id"):
            result.add_error("Missing revision_id")

        if not transformed_data.get("uri"):
            result.add_error("Missing document URI")

        return result

    def extract(self, validated_data: dict[str, Any]) -> dict[str, Any]:
        """
        Extract information from driver's license document.

        In real implementation, would:
        - Download document from GCS
        - Run OCR or Document AI
        - Extract name, DOB, license number, expiration
        - Validate against application data
        """
        _document = validated_data.get("document", {})
        config = validated_data.get("config", {})

        # In real implementation:
        # 1. Download document from validated_data['uri']
        # 2. Run OCR/Document AI
        # 3. Extract fields
        # 4. Validate expiration if config requires

        # Mock extracted data for testing
        output = {
            "document_type": "drivers_license",
            "license_number": "DL123456789",  # Would be extracted via OCR
            "holder_name": "John Doe",
            "date_of_birth": "1985-05-15",
            "expiration_date": "2025-12-31",
            "state": "CA",
            "is_expired": False,
            "photo_present": True,
            "verification_status": "verified",
        }

        # Validate expiration if required
        if config.get("check_expiration", True):
            # In real implementation, check actual date
            if output["is_expired"]:
                output["verification_status"] = "expired"

        # Check photo requirement
        if config.get("require_photo", True):
            if not output["photo_present"]:
                output["verification_status"] = "missing_photo"

        # Track cost for OCR processing
        self._add_cost(3.0, "ocr_processing")
        self._add_cost(1.0, "document_validation")

        return output

    def validate_output(self, output: dict[str, Any]) -> ValidationResult:
        """
        Validate extraction output.
        """
        result = ValidationResult(is_valid=True)

        # Check required fields
        required_fields = [
            "document_type",
            "license_number",
            "holder_name",
            "verification_status",
        ]

        for field in required_fields:
            if field not in output:
                result.add_error(f"Missing required field: {field}")

        # Check verification status
        valid_statuses = ["verified", "expired", "missing_photo", "invalid"]
        if output.get("verification_status") not in valid_statuses:
            result.add_error(f"Invalid verification status: {output.get('verification_status')}")

        # Add warnings for problematic documents
        if output.get("is_expired", False):
            result.add_warning("Document is expired")

        if not output.get("photo_present", False):
            result.add_warning("Document photo is missing")

        return result

    @staticmethod
    def consolidate(executions: list[Any]) -> dict[str, Any]:
        """
        Consolidate multiple document executions.

        For DOCUMENT type, each execution processes one document.
        Consolidation might combine results from multiple documents
        (e.g., multiple driver's licenses from different owners).
        """
        if not executions:
            return {}

        # Collect all document results
        all_documents = []
        verified_count = 0
        expired_count = 0

        for execution in executions:
            output = getattr(execution, "output", execution)
            if isinstance(output, dict):
                all_documents.append(output)

                status = output.get("verification_status")
                if status == "verified":
                    verified_count += 1
                elif status == "expired":
                    expired_count += 1

        # Return consolidated factors with f_ prefix
        return {
            "f_total_licenses_processed": len(all_documents),
            "f_verified_licenses_count": verified_count,
            "f_expired_licenses_count": expired_count,
            "f_verification_rate": (
                verified_count / len(all_documents)
                if all_documents else 0.0
            ),
            "f_all_licenses_valid": expired_count == 0 and verified_count == len(all_documents),
        }

