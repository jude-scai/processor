"""
Comprehensive unit tests for BaseProcessor and all three processor types.

Tests cover:
- All three processor types (APPLICATION, STIPULATION, DOCUMENT)
- Complete 3-phase execution pipeline
- Cost tracking
- Event emission
- Document tracking
- Validation (input and output)
- Error handling for each phase
- Atomic success/failure semantics
- Consolidation logic
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, MagicMock
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from aura.processing_engine.models import (
    ExecutionStatus,
    ProcessorType,
    ExecutionPayload,
    ValidationResult,
)
from aura.processing_engine.exceptions import (
    InputValidationError,
    TransformationError,
    FactorExtractionError,
    ResultValidationError,
)
from aura.processing_engine.repositories.processor_repository import ProcessorRepository
from aura.processing_engine.repositories.execution_repository import ExecutionRepository
from .processors.application_processor import ApplicationProcessor
from .processors.stipulation_processor import StipulationProcessor
from .processors.document_processor import DocumentProcessor


class TestBaseProcessorConfiguration:
    """Test processor configuration and constants."""

    def test_application_processor_configuration(self):
        """Test APPLICATION processor has correct configuration."""
        processor = ApplicationProcessor()

        assert processor.PROCESSOR_NAME == "p_test_application"
        assert processor.PROCESSOR_TYPE == ProcessorType.APPLICATION
        assert "application_form" in processor.PROCESSOR_TRIGGERS
        assert isinstance(processor.CONFIG, dict)

    def test_stipulation_processor_configuration(self):
        """Test STIPULATION processor has correct configuration."""
        processor = StipulationProcessor()

        assert processor.PROCESSOR_NAME == "p_test_stipulation"
        assert processor.PROCESSOR_TYPE == ProcessorType.STIPULATION
        assert "documents_list" in processor.PROCESSOR_TRIGGERS
        assert processor.CONFIG.get("minimum_document") == 3

    def test_document_processor_configuration(self):
        """Test DOCUMENT processor has correct configuration."""
        processor = DocumentProcessor()

        assert processor.PROCESSOR_NAME == "p_test_document"
        assert processor.PROCESSOR_TYPE == ProcessorType.DOCUMENT
        assert "documents_list" in processor.PROCESSOR_TRIGGERS
        assert processor.CONFIG.get("require_photo") is True

    def test_get_config_with_repository(self):
        """Test get_config uses repository to fetch effective configuration."""
        # Create mock repository
        mock_repo = Mock(spec=ProcessorRepository)
        mock_repo.get_effective_config.return_value = {
            "minimum_document": 5,  # Override from database
            "analysis_window_months": 12,  # Override from database
        }

        # Create processor with repository
        processor = StipulationProcessor(processor_repo=mock_repo)
        processor._underwriting_processor_id = "uwp_123"

        # Call get_config
        config = processor.get_config()

        # Verify repository was called
        mock_repo.get_effective_config.assert_called_once_with("uwp_123")

        # Verify config merge (system defaults + database overrides)
        assert config["minimum_document"] == 5  # DB override
        assert config["analysis_window_months"] == 12  # DB override

    def test_get_config_merges_system_defaults_with_database(self):
        """Test that get_config properly merges system defaults with DB config."""
        mock_repo = Mock(spec=ProcessorRepository)
        mock_repo.get_effective_config.return_value = {
            "require_ein": False,  # Override system default
            "custom_field": "custom_value",  # New field from DB
        }

        processor = ApplicationProcessor(processor_repo=mock_repo)
        processor._underwriting_processor_id = "uwp_456"

        config = processor.get_config()

        # System default that wasn't overridden should still be present
        assert "require_industry" in config

        # Database override should take precedence
        assert config["require_ein"] is False

        # New field from database should be included
        assert config["custom_field"] == "custom_value"

    def test_get_config_with_multiple_calls(self):
        """Test get_config can be called multiple times."""
        mock_processor_repo = Mock(spec=ProcessorRepository)
        mock_processor_repo.get_effective_config.return_value = {
            "minimum_document": 4
        }

        processor = StipulationProcessor(processor_repo=mock_processor_repo)
        processor._underwriting_processor_id = "uwp_789"

        # Call multiple times
        config1 = processor.get_config()
        config2 = processor.get_config()

        # Both should return same config
        assert config1 == config2
        assert config1["minimum_document"] == 4

        # Verify repository was called twice (once per call)
        assert mock_processor_repo.get_effective_config.call_count == 2

    def test_get_config_raises_without_repo(self):
        """Test get_config raises error if repo not initialized."""
        processor = ApplicationProcessor()
        processor._underwriting_processor_id = "uwp_123"

        with pytest.raises(ValueError, match="Processor repository not initialized"):
            processor.get_config()

    def test_get_config_raises_without_underwriting_processor_id(self):
        """Test get_config raises error if underwriting_processor_id not set."""
        mock_repo = Mock(spec=ProcessorRepository)
        processor = ApplicationProcessor(processor_repo=mock_repo)

        with pytest.raises(ValueError, match="Underwriting processor ID not set"):
            processor.get_config()


class TestApplicationProcessor:
    """Comprehensive tests for APPLICATION type processor."""

    @pytest.fixture
    def valid_payload(self):
        """Create valid application payload."""
        return ExecutionPayload(
            underwriting_id="uw_app_001",
            underwriting_processor_id="uwp_app_001",
            application_form={
                "merchant.name": "Test Company Inc",
                "merchant.ein": "12-3456789",
                "merchant.industry": "Technology",
                "merchant.state_of_incorporation": "CA",
                "merchant.entity_type": "LLC",
            },
            owners_list=[
                {"first_name": "John", "last_name": "Doe", "primary_owner": True},
                {"first_name": "Jane", "last_name": "Smith", "primary_owner": False},
            ],
        )

    @pytest.fixture
    def processor(self):
        """Create processor instance."""
        return ApplicationProcessor()

    def test_successful_execution(self, processor, valid_payload):
        """Test successful APPLICATION processor execution."""
        result = processor.execute(
            execution_id="exec_001",
            underwriting_processor_id="uwp_001",
            payload=valid_payload,
        )

        assert result.status == ExecutionStatus.COMPLETED
        assert result.is_successful()
        assert result.execution_id == "exec_001"
        assert result.processor_name == "p_test_application"
        assert result.duration_seconds >= 0
        assert result.error_message is None

    def test_output_structure(self, processor, valid_payload):
        """Test APPLICATION processor output contains expected fields."""
        result = processor.execute(
            execution_id="exec_002",
            underwriting_processor_id="uwp_001",
            payload=valid_payload,
        )

        assert "business_name" in result.output
        assert "business_ein" in result.output
        assert "business_industry" in result.output
        assert "owner_count" in result.output
        assert "has_primary_owner" in result.output

        assert result.output["business_name"] == "Test Company Inc"
        assert result.output["owner_count"] == 2
        assert result.output["has_primary_owner"] is True

    def test_cost_tracking(self, processor, valid_payload):
        """Test cost tracking for APPLICATION processor."""
        result = processor.execute(
            execution_id="exec_003",
            underwriting_processor_id="uwp_001",
            payload=valid_payload,
        )

        assert result.total_cost_cents > 0
        assert "application_processing" in result.cost_breakdown
        assert result.cost_breakdown["application_processing"] > 0

    def test_missing_required_field_validation(self, processor):
        """Test validation failure when required field is missing."""
        invalid_payload = ExecutionPayload(
            underwriting_id="uw_app_002",
            underwriting_processor_id="uwp_002",
            application_form={
                "merchant.name": "Test Company",
                # Missing merchant.ein
            },
        )

        result = processor.execute(
            execution_id="exec_004",
            underwriting_processor_id="uwp_002",
            payload=invalid_payload,
        )

        assert result.status == ExecutionStatus.FAILED
        assert result.is_failed()
        assert result.error_phase == "pre-extraction"
        assert "EIN" in result.error_message or "ein" in result.error_message

    def test_no_owners_warning(self, processor):
        """Test warning when no owners provided."""
        payload_no_owners = ExecutionPayload(
            underwriting_id="uw_app_003",
            underwriting_processor_id="uwp_003",
            application_form={
                "merchant.name": "Test Company",
                "merchant.ein": "12-3456789",
                "merchant.industry": "Tech",
            },
            owners_list=[],
        )

        result = processor.execute(
            execution_id="exec_005",
            underwriting_processor_id="uwp_003",
            payload=payload_no_owners,
        )

        # Should still succeed but with warning
        assert result.status == ExecutionStatus.COMPLETED
        assert result.output["owner_count"] == 0


class TestStipulationProcessor:
    """Comprehensive tests for STIPULATION type processor."""

    @pytest.fixture
    def valid_payload(self):
        """Create valid stipulation payload with multiple documents."""
        return ExecutionPayload(
            underwriting_id="uw_stip_001",
            underwriting_processor_id="uwp_stip_001",
            documents_list=[
                {
                    "stipulation_type": "s_bank_statement",
                    "revision_id": "rev_001",
                    "document_id": "doc_001",
                    "uri": "gs://test/stmt1.pdf",
                },
                {
                    "stipulation_type": "s_bank_statement",
                    "revision_id": "rev_002",
                    "document_id": "doc_002",
                    "uri": "gs://test/stmt2.pdf",
                },
                {
                    "stipulation_type": "s_bank_statement",
                    "revision_id": "rev_003",
                    "document_id": "doc_003",
                    "uri": "gs://test/stmt3.pdf",
                },
            ],
            config={"minimum_document": 3},
        )

    @pytest.fixture
    def processor(self):
        """Create processor instance."""
        return StipulationProcessor()

    def test_successful_execution(self, processor, valid_payload):
        """Test successful STIPULATION processor execution."""
        result = processor.execute(
            execution_id="exec_stip_001",
            underwriting_processor_id="uwp_stip_001",
            payload=valid_payload,
        )

        assert result.status == ExecutionStatus.COMPLETED
        assert result.is_successful()
        assert result.processor_name == "p_test_stipulation"

    def test_output_structure(self, processor, valid_payload):
        """Test STIPULATION processor output contains expected fields."""
        result = processor.execute(
            execution_id="exec_stip_002",
            underwriting_processor_id="uwp_stip_001",
            payload=valid_payload,
        )

        assert "monthly_revenues" in result.output
        assert "avg_monthly_revenue" in result.output
        assert "min_monthly_revenue" in result.output
        assert "max_monthly_revenue" in result.output
        assert "months_analyzed" in result.output

        assert isinstance(result.output["monthly_revenues"], list)
        assert len(result.output["monthly_revenues"]) == 3
        assert result.output["months_analyzed"] == 3

    def test_document_tracking(self, processor, valid_payload):
        """Test document revision tracking for STIPULATION processor."""
        result = processor.execute(
            execution_id="exec_stip_003",
            underwriting_processor_id="uwp_stip_001",
            payload=valid_payload,
        )

        assert len(result.document_revision_ids) == 3
        assert "rev_001" in result.document_revision_ids
        assert "rev_002" in result.document_revision_ids
        assert "rev_003" in result.document_revision_ids
        assert result.document_ids_hash is not None

    def test_cost_tracking_per_document(self, processor, valid_payload):
        """Test cost tracking scales with document count."""
        result = processor.execute(
            execution_id="exec_stip_004",
            underwriting_processor_id="uwp_stip_001",
            payload=valid_payload,
        )

        # Cost should be 2.0 cents per document * 3 documents = 6.0 cents
        assert result.total_cost_cents == 6.0
        assert "document_processing" in result.cost_breakdown

    def test_insufficient_documents_validation(self, processor):
        """Test validation failure when document count is below minimum."""
        insufficient_payload = ExecutionPayload(
            underwriting_id="uw_stip_002",
            underwriting_processor_id="uwp_stip_002",
            documents_list=[
                {
                    "stipulation_type": "s_bank_statement",
                    "revision_id": "rev_001",
                    "document_id": "doc_001",
                    "uri": "gs://test/stmt1.pdf",
                },
            ],
            config={"minimum_document": 3},
        )

        result = processor.execute(
            execution_id="exec_stip_005",
            underwriting_processor_id="uwp_stip_002",
            payload=insufficient_payload,
        )

        assert result.status == ExecutionStatus.FAILED
        assert result.error_phase == "pre-extraction"
        assert "Insufficient" in result.error_message or "document" in result.error_message

    def test_should_execute_logic(self, processor):
        """Test should_execute static method."""
        # Sufficient documents
        should_exec, reason = processor.should_execute({
            "documents_list": [
                {"stipulation_type": "s_bank_statement"},
                {"stipulation_type": "s_bank_statement"},
                {"stipulation_type": "s_bank_statement"},
            ],
            "config": {"minimum_document": 3},
        })
        assert should_exec is True
        assert reason is None

        # Insufficient documents
        should_exec, reason = processor.should_execute({
            "documents_list": [
                {"stipulation_type": "s_bank_statement"},
            ],
            "config": {"minimum_document": 3},
        })
        assert should_exec is False
        assert reason is not None
        assert "minimum" in reason.lower()

    def test_consolidation_logic(self, processor):
        """Test consolidation of multiple executions."""
        # Create mock execution outputs
        class MockExecution:
            def __init__(self, output):
                self.output = output

        executions = [
            MockExecution({
                "monthly_revenues": [45000.0, 46000.0],
                "months_analyzed": 2,
            }),
            MockExecution({
                "monthly_revenues": [47000.0, 48000.0],
                "months_analyzed": 2,
            }),
        ]

        consolidated = processor.consolidate(executions)

        assert "f_revenue_monthly_avg" in consolidated
        assert "f_revenue_monthly_min" in consolidated
        assert "f_revenue_monthly_max" in consolidated
        assert "f_total_months_analyzed" in consolidated

        # Check values
        assert consolidated["f_revenue_monthly_min"] == 45000.0
        assert consolidated["f_revenue_monthly_max"] == 48000.0
        assert consolidated["f_total_months_analyzed"] == 4

    def test_empty_consolidation(self, processor):
        """Test consolidation with no executions."""
        consolidated = processor.consolidate([])
        assert consolidated == {}


class TestDocumentProcessor:
    """Comprehensive tests for DOCUMENT type processor."""

    @pytest.fixture
    def valid_payload(self):
        """Create valid document payload."""
        return ExecutionPayload(
            underwriting_id="uw_doc_001",
            underwriting_processor_id="uwp_doc_001",
            documents_list=[
                {
                    "stipulation_type": "s_drivers_license",
                    "revision_id": "rev_dl_001",
                    "document_id": "doc_dl_001",
                    "uri": "gs://test/license.pdf",
                },
            ],
            config={"require_photo": True, "check_expiration": True},
        )

    @pytest.fixture
    def processor(self):
        """Create processor instance."""
        return DocumentProcessor()

    def test_successful_execution(self, processor, valid_payload):
        """Test successful DOCUMENT processor execution."""
        result = processor.execute(
            execution_id="exec_doc_001",
            underwriting_processor_id="uwp_doc_001",
            payload=valid_payload,
        )

        assert result.status == ExecutionStatus.COMPLETED
        assert result.is_successful()
        assert result.processor_name == "p_test_document"

    def test_output_structure(self, processor, valid_payload):
        """Test DOCUMENT processor output contains expected fields."""
        result = processor.execute(
            execution_id="exec_doc_002",
            underwriting_processor_id="uwp_doc_001",
            payload=valid_payload,
        )

        assert "document_type" in result.output
        assert "license_number" in result.output
        assert "holder_name" in result.output
        assert "verification_status" in result.output
        assert "is_expired" in result.output
        assert "photo_present" in result.output

        assert result.output["document_type"] == "drivers_license"
        assert result.output["verification_status"] == "verified"

    def test_document_tracking_single_document(self, processor, valid_payload):
        """Test document tracking for single document."""
        result = processor.execute(
            execution_id="exec_doc_003",
            underwriting_processor_id="uwp_doc_001",
            payload=valid_payload,
        )

        assert len(result.document_revision_ids) == 1
        assert "rev_dl_001" in result.document_revision_ids
        assert result.document_ids_hash is not None

    def test_cost_tracking_ocr_and_validation(self, processor, valid_payload):
        """Test cost tracking includes OCR and validation costs."""
        result = processor.execute(
            execution_id="exec_doc_004",
            underwriting_processor_id="uwp_doc_001",
            payload=valid_payload,
        )

        # Should have OCR cost (3.0) + validation cost (1.0) = 4.0 cents
        assert result.total_cost_cents == 4.0
        assert "ocr_processing" in result.cost_breakdown
        assert "document_validation" in result.cost_breakdown
        assert result.cost_breakdown["ocr_processing"] == 3.0
        assert result.cost_breakdown["document_validation"] == 1.0

    def test_consolidation_multiple_documents(self, processor):
        """Test consolidation of multiple driver's licenses."""
        class MockExecution:
            def __init__(self, output):
                self.output = output

        executions = [
            MockExecution({"verification_status": "verified"}),
            MockExecution({"verification_status": "verified"}),
            MockExecution({"verification_status": "expired"}),
        ]

        consolidated = processor.consolidate(executions)

        assert "f_total_licenses_processed" in consolidated
        assert "f_verified_licenses_count" in consolidated
        assert "f_expired_licenses_count" in consolidated
        assert "f_verification_rate" in consolidated
        assert "f_all_licenses_valid" in consolidated

        assert consolidated["f_total_licenses_processed"] == 3
        assert consolidated["f_verified_licenses_count"] == 2
        assert consolidated["f_expired_licenses_count"] == 1
        assert consolidated["f_verification_rate"] == pytest.approx(2/3)
        assert consolidated["f_all_licenses_valid"] is False


class TestExecutionPipeline:
    """Test the 3-phase execution pipeline."""

    def test_phase_order_application(self):
        """Test phases execute in correct order for APPLICATION processor."""
        processor = ApplicationProcessor()

        # Track method calls
        calls = []
        original_transform = processor.transform_input
        original_validate_input = processor.validate_input
        original_extract = processor.extract
        original_validate_output = processor.validate_output

        def track_transform(*args, **kwargs):
            calls.append("transform")
            return original_transform(*args, **kwargs)

        def track_validate_input(*args, **kwargs):
            calls.append("validate_input")
            return original_validate_input(*args, **kwargs)

        def track_extract(*args, **kwargs):
            calls.append("extract")
            return original_extract(*args, **kwargs)

        def track_validate_output(*args, **kwargs):
            calls.append("validate_output")
            return original_validate_output(*args, **kwargs)

        processor.transform_input = track_transform
        processor.validate_input = track_validate_input
        processor.extract = track_extract
        processor.validate_output = track_validate_output

        payload = ExecutionPayload(
            underwriting_id="uw_pipeline_001",
            underwriting_processor_id="uwp_pipeline_001",
            application_form={
                "merchant.name": "Test",
                "merchant.ein": "12-3456789",
                "merchant.industry": "Tech",
            },
        )

        processor.execute("exec_001", "uwp_001", payload)

        # Verify phase order
        assert calls == ["transform", "validate_input", "extract", "validate_output"]

    def test_atomic_failure_in_transformation(self):
        """Test that transformation failure stops execution immediately."""
        processor = ApplicationProcessor()

        # Create invalid payload that will fail transformation
        invalid_payload = ExecutionPayload(
            underwriting_id="uw_fail_001",
            underwriting_processor_id="uwp_fail_001",
            application_form={},  # Empty form
        )

        result = processor.execute("exec_fail_001", "uwp_fail_001", invalid_payload)

        assert result.status == ExecutionStatus.FAILED
        assert result.error_phase == "pre-extraction"
        # Output should be empty since extraction never ran
        assert result.output == {}


class TestErrorHandling:
    """Test error handling across all phases."""

    def test_error_contains_phase_information(self):
        """Test that errors include phase information."""
        processor = ApplicationProcessor()

        invalid_payload = ExecutionPayload(
            underwriting_id="uw_err_001",
            underwriting_processor_id="uwp_err_001",
            application_form={"merchant.name": "Test"},  # Missing EIN
        )

        result = processor.execute("exec_err_001", "uwp_err_001", invalid_payload)

        assert result.error_phase in ["pre-extraction", "extraction", "post-extraction"]
        assert result.error_type is not None
        assert result.error_message is not None


class TestProcessingResult:
    """Test ProcessingResult model."""

    def test_result_has_all_required_fields(self):
        """Test ProcessingResult contains all expected fields."""
        processor = ApplicationProcessor()

        payload = ExecutionPayload(
            underwriting_id="uw_result_001",
            underwriting_processor_id="uwp_result_001",
            application_form={
                "merchant.name": "Test",
                "merchant.ein": "12-3456789",
                "merchant.industry": "Tech",
            },
        )

        result = processor.execute("exec_result_001", "uwp_result_001", payload)

        # Check all required fields exist
        assert hasattr(result, "execution_id")
        assert hasattr(result, "processor_name")
        assert hasattr(result, "underwriting_processor_id")
        assert hasattr(result, "status")
        assert hasattr(result, "started_at")
        assert hasattr(result, "completed_at")
        assert hasattr(result, "duration_seconds")
        assert hasattr(result, "output")
        assert hasattr(result, "total_cost_cents")
        assert hasattr(result, "cost_breakdown")
        assert hasattr(result, "error_message")
        assert hasattr(result, "error_type")
        assert hasattr(result, "error_phase")
        assert hasattr(result, "document_revision_ids")
        assert hasattr(result, "document_ids_hash")

    def test_result_to_dict_serialization(self):
        """Test ProcessingResult can be serialized to dict."""
        processor = ApplicationProcessor()

        payload = ExecutionPayload(
            underwriting_id="uw_serial_001",
            underwriting_processor_id="uwp_serial_001",
            application_form={
                "merchant.name": "Test",
                "merchant.ein": "12-3456789",
                "merchant.industry": "Tech",
            },
        )

        result = processor.execute("exec_serial_001", "uwp_serial_001", payload)
        result_dict = result.to_dict()

        assert isinstance(result_dict, dict)
        assert "execution_id" in result_dict
        assert "status" in result_dict
        assert "output" in result_dict


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

