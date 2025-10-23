"""
Comprehensive tests for processor and execution repositories.

Tests the repository layer for database operations, including:
- Processor configuration retrieval
- Execution creation and management
- Status tracking and updates
- Supersession relationships
"""

import pytest
from datetime import datetime
from typing import Any
from unittest.mock import Mock, MagicMock
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from aura.processing_engine.repositories.processor_repository import ProcessorRepository
from aura.processing_engine.repositories.execution_repository import ExecutionRepository


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def mock_db():
    """Create a mock database connection."""
    return Mock()


@pytest.fixture
def processor_repo(mock_db):
    """Create a ProcessorRepository instance with mock DB."""
    return ProcessorRepository(mock_db)


@pytest.fixture
def execution_repo(mock_db):
    """Create an ExecutionRepository instance with mock DB."""
    return ExecutionRepository(mock_db)


@pytest.fixture
def sample_purchased_processor():
    """Sample purchased processor record."""
    return {
        "id": "pp_123",
        "organization_id": "org_456",
        "processor": "p_bank_statement",
        "name": "Bank Statement Processor",
        "auto": True,
        "status": "active",
        "config": {"minimum_document": 3, "analysis_window_months": 6},
        "price_amount": 500,
        "price_unit": "execution",
        "price_currency": "USD",
        "purchased_at": datetime(2024, 1, 1),
        "purchased_by": "user_123",
    }


@pytest.fixture
def sample_underwriting_processor():
    """Sample underwriting processor record."""
    return {
        "id": "up_789",
        "organization_id": "org_456",
        "underwriting_id": "uw_001",
        "purchased_processor_id": "pp_123",
        "processor": "p_bank_statement",
        "name": "Bank Statement Processor",
        "auto": True,
        "enabled": True,
        "config_override": {"minimum_document": 5},
        "effective_config": {"minimum_document": 5, "analysis_window_months": 6},
        "current_executions_list": ["exec_001", "exec_002"],
        "purchased_config": {"minimum_document": 3, "analysis_window_months": 6},
        "price_amount": 500,
        "price_unit": "execution",
    }


@pytest.fixture
def sample_execution():
    """Sample execution record."""
    return {
        "id": "exec_001",
        "organization_id": "org_456",
        "underwriting_id": "uw_001",
        "underwriting_processor_id": "up_789",
        "processor": "p_bank_statement",
        "status": "completed",
        "enabled": True,
        "payload": {
            "documents_list": [
                {"revision_id": "rev_001", "stipulation_type": "s_bank_statement"}
            ]
        },
        "payload_hash": "hash_abc123",
        "output": {"monthly_revenues": [45000.0], "avg_monthly_revenue": 45000.0},
        "factors_delta": {"f_avg_monthly_revenue": 45000.0},
        "document_revision_ids": ["rev_001"],
        "document_ids_hash": "doc_hash_123",
        "run_cost_cents": 50,
        "started_at": datetime(2024, 1, 15, 10, 0, 0),
        "completed_at": datetime(2024, 1, 15, 10, 5, 0),
        "failed_code": None,
        "failed_reason": None,
        "updated_execution_id": None,
        "created_at": datetime(2024, 1, 15, 9, 55, 0),
        "updated_at": datetime(2024, 1, 15, 10, 5, 0),
    }


# =============================================================================
# PROCESSOR REPOSITORY TESTS
# =============================================================================


class TestProcessorRepositoryStructure:
    """Test ProcessorRepository class structure and initialization."""

    def test_repository_initialization(self, processor_repo, mock_db):
        """Test that repository initializes correctly with DB connection."""
        assert processor_repo.db is mock_db
        assert isinstance(processor_repo, ProcessorRepository)

    def test_repository_has_required_methods(self, processor_repo):
        """Test that repository has all required methods."""
        required_methods = [
            "get_processor_catalog",
            "get_purchased_processor_by_id",
            "get_purchased_processors_by_organization",
            "get_underwriting_processor_by_id",
            "get_underwriting_processors",
            "update_current_executions_list",
            "get_effective_config",
            "get_processor_by_name",
        ]
        for method_name in required_methods:
            assert hasattr(processor_repo, method_name)
            assert callable(getattr(processor_repo, method_name))


class TestProcessorCatalog:
    """Test system processor catalog operations."""

    def test_get_processor_catalog_returns_list(self, processor_repo):
        """Test that get_processor_catalog returns a list."""
        result = processor_repo.get_processor_catalog()
        assert isinstance(result, list)


class TestPurchasedProcessors:
    """Test purchased processor operations."""

    def test_get_purchased_processor_by_id_returns_none_when_not_implemented(
        self, processor_repo
    ):
        """Test that get_purchased_processor_by_id returns None (not implemented yet)."""
        result = processor_repo.get_purchased_processor_by_id("pp_123")
        assert result is None

    def test_get_purchased_processors_by_organization_returns_empty_list(
        self, processor_repo
    ):
        """Test that get_purchased_processors_by_organization returns empty list."""
        result = processor_repo.get_purchased_processors_by_organization("org_123")
        assert result == []

    def test_get_purchased_processors_with_filters(self, processor_repo):
        """Test filtering purchased processors by enabled/auto flags."""
        result = processor_repo.get_purchased_processors_by_organization(
            "org_123", enabled_only=True, auto_only=True
        )
        assert result == []


class TestUnderwritingProcessors:
    """Test underwriting processor operations."""

    def test_get_underwriting_processor_by_id_returns_none(self, processor_repo):
        """Test that get_underwriting_processor_by_id returns None (not implemented)."""
        result = processor_repo.get_underwriting_processor_by_id("up_789")
        assert result is None

    def test_get_underwriting_processors_returns_empty_list(self, processor_repo):
        """Test that get_underwriting_processors returns empty list."""
        result = processor_repo.get_underwriting_processors("uw_001")
        assert result == []

    def test_get_underwriting_processors_with_filters(self, processor_repo):
        """Test filtering underwriting processors by enabled/auto flags."""
        result = processor_repo.get_underwriting_processors(
            "uw_001", enabled_only=True, auto_only=True
        )
        assert result == []

    def test_update_current_executions_list_returns_false(self, processor_repo):
        """Test that update_current_executions_list returns False (not implemented)."""
        result = processor_repo.update_current_executions_list(
            "up_789", ["exec_001", "exec_002"]
        )
        assert result is False


class TestProcessorConfiguration:
    """Test processor configuration operations."""

    def test_get_effective_config_with_no_processor(self, processor_repo):
        """Test get_effective_config returns empty dict when processor not found."""
        result = processor_repo.get_effective_config("up_nonexistent")
        assert result == {}

    def test_get_processor_by_name_returns_none(self, processor_repo):
        """Test that get_processor_by_name returns None (not implemented)."""
        result = processor_repo.get_processor_by_name("p_bank_statement", "org_123")
        assert result is None


# =============================================================================
# EXECUTION REPOSITORY TESTS
# =============================================================================


class TestExecutionRepositoryStructure:
    """Test ExecutionRepository class structure and initialization."""

    def test_repository_initialization(self, execution_repo, mock_db):
        """Test that repository initializes correctly with DB connection."""
        assert execution_repo.db is mock_db
        assert isinstance(execution_repo, ExecutionRepository)

    def test_repository_has_required_methods(self, execution_repo):
        """Test that repository has all required methods."""
        required_methods = [
            "create_execution",
            "find_execution_by_hash",
            "update_execution_status",
            "save_execution_result",
            "get_execution_by_id",
            "get_active_executions",
            "get_executions_by_underwriting",
            "mark_execution_superseded",
            "get_execution_chain",
            "activate_execution",
            "deactivate_execution",
            "get_execution_count",
        ]
        for method_name in required_methods:
            assert hasattr(execution_repo, method_name)
            assert callable(getattr(execution_repo, method_name))


class TestExecutionCreation:
    """Test execution creation operations."""

    def test_create_execution_generates_uuid(self, execution_repo):
        """Test that create_execution generates a valid UUID."""
        execution_id = execution_repo.create_execution(
            underwriting_id="uw_001",
            underwriting_processor_id="up_789",
            organization_id="org_456",
            processor_name="p_bank_statement",
            payload={"test": "data"},
            payload_hash="hash_123",
        )

        # Should return a UUID string
        assert isinstance(execution_id, str)
        assert len(execution_id) == 36  # UUID format
        assert execution_id.count("-") == 4  # UUID has 4 dashes

    def test_create_execution_with_document_ids(self, execution_repo):
        """Test creating execution with document tracking."""
        execution_id = execution_repo.create_execution(
            underwriting_id="uw_001",
            underwriting_processor_id="up_789",
            organization_id="org_456",
            processor_name="p_bank_statement",
            payload={"test": "data"},
            payload_hash="hash_123",
            document_revision_ids=["rev_001", "rev_002"],
            document_ids_hash="doc_hash_123",
        )

        assert isinstance(execution_id, str)

    def test_find_execution_by_hash_returns_none(self, execution_repo):
        """Test that find_execution_by_hash returns None (not implemented)."""
        result = execution_repo.find_execution_by_hash("up_789", "hash_123")
        assert result is None


class TestExecutionStatusUpdates:
    """Test execution status update operations."""

    def test_update_execution_status_returns_false(self, execution_repo):
        """Test that update_execution_status returns False (not implemented)."""
        result = execution_repo.update_execution_status(
            "exec_001", "running", started_at=datetime.utcnow()
        )
        assert result is False

    def test_update_execution_status_with_completion(self, execution_repo):
        """Test updating status to completed with timestamp."""
        result = execution_repo.update_execution_status(
            "exec_001", "completed", completed_at=datetime.utcnow()
        )
        assert result is False  # Not implemented yet

    def test_update_execution_status_with_failure(self, execution_repo):
        """Test updating status to failed with error details."""
        result = execution_repo.update_execution_status(
            "exec_001",
            "failed",
            failed_code="VALIDATION_ERROR",
            failed_reason="Missing required field: merchant.name",
        )
        assert result is False  # Not implemented yet

    def test_save_execution_result_returns_false(self, execution_repo):
        """Test that save_execution_result returns False (not implemented)."""
        result = execution_repo.save_execution_result(
            execution_id="exec_001",
            output={"test": "output"},
            factors_delta={"f_test": 123},
            run_cost_cents=50,
            completed_at=datetime.utcnow(),
        )
        assert result is False


class TestExecutionRetrieval:
    """Test execution retrieval operations."""

    def test_get_execution_by_id_returns_none(self, execution_repo):
        """Test that get_execution_by_id returns None (not implemented)."""
        result = execution_repo.get_execution_by_id("exec_001")
        assert result is None

    def test_get_active_executions_returns_empty_list(self, execution_repo):
        """Test that get_active_executions returns empty list."""
        result = execution_repo.get_active_executions("up_789")
        assert result == []

    def test_get_executions_by_underwriting_returns_empty_list(self, execution_repo):
        """Test that get_executions_by_underwriting returns empty list."""
        result = execution_repo.get_executions_by_underwriting("uw_001")
        assert result == []

    def test_get_executions_by_underwriting_with_filters(self, execution_repo):
        """Test filtering executions by processor and status."""
        result = execution_repo.get_executions_by_underwriting(
            "uw_001", processor_name="p_bank_statement", status="completed"
        )
        assert result == []


class TestSupersession:
    """Test execution supersession operations."""

    def test_mark_execution_superseded_returns_false(self, execution_repo):
        """Test that mark_execution_superseded returns False (not implemented)."""
        result = execution_repo.mark_execution_superseded("exec_001", "exec_002")
        assert result is False

    def test_get_execution_chain_returns_empty_list(self, execution_repo):
        """Test that get_execution_chain returns empty list when execution not found."""
        result = execution_repo.get_execution_chain("exec_nonexistent")
        assert result == []


class TestActivationDeactivation:
    """Test execution activation/deactivation operations."""

    def test_activate_execution_returns_false(self, execution_repo):
        """Test that activate_execution returns False (not implemented)."""
        result = execution_repo.activate_execution("exec_001")
        assert result is False

    def test_deactivate_execution_returns_false(self, execution_repo):
        """Test that deactivate_execution returns False (not implemented)."""
        result = execution_repo.deactivate_execution("exec_001")
        assert result is False


class TestHelperMethods:
    """Test repository helper methods."""

    def test_generate_uuid_returns_valid_format(self, execution_repo):
        """Test that _generate_uuid creates valid UUID strings."""
        uuid1 = execution_repo._generate_uuid()
        uuid2 = execution_repo._generate_uuid()

        # Should be strings
        assert isinstance(uuid1, str)
        assert isinstance(uuid2, str)

        # Should be different
        assert uuid1 != uuid2

        # Should be valid UUID format
        assert len(uuid1) == 36
        assert uuid1.count("-") == 4

    def test_get_execution_count_returns_zero(self, execution_repo):
        """Test that get_execution_count returns 0 (not implemented)."""
        result = execution_repo.get_execution_count("uw_001")
        assert result == 0

    def test_get_execution_count_with_processor_filter(self, execution_repo):
        """Test get_execution_count with processor filter."""
        result = execution_repo.get_execution_count(
            "uw_001", processor_name="p_bank_statement"
        )
        assert result == 0


# =============================================================================
# INTEGRATION PATTERNS TESTS
# =============================================================================


class TestRepositoryPatterns:
    """Test common repository usage patterns."""

    def test_processor_config_resolution_pattern(
        self, processor_repo, sample_underwriting_processor
    ):
        """Test the pattern of resolving effective processor configuration."""
        # This tests the expected flow when implementation is complete
        # For now, it demonstrates the expected behavior

        # Step 1: Get underwriting processor
        # up = processor_repo.get_underwriting_processor_by_id("up_789")

        # Step 2: Get effective config
        config = processor_repo.get_effective_config("up_789")

        # Currently returns empty dict (not implemented)
        assert isinstance(config, dict)

    def test_execution_lifecycle_pattern(self, execution_repo):
        """Test the full execution lifecycle pattern."""
        # Step 1: Create execution
        exec_id = execution_repo.create_execution(
            underwriting_id="uw_001",
            underwriting_processor_id="up_789",
            organization_id="org_456",
            processor_name="p_bank_statement",
            payload={"test": "data"},
            payload_hash="hash_123",
        )
        assert exec_id is not None

        # Step 2: Update to running
        execution_repo.update_execution_status(exec_id, "running")

        # Step 3: Save result
        execution_repo.save_execution_result(
            exec_id,
            output={"result": "data"},
            factors_delta={"f_test": 123},
            run_cost_cents=50,
            completed_at=datetime.utcnow(),
        )

    def test_execution_deduplication_pattern(self, execution_repo):
        """Test the pattern for deduplicating executions by hash."""
        payload_hash = "hash_abc123"

        # Step 1: Check if execution exists
        existing = execution_repo.find_execution_by_hash("up_789", payload_hash)

        # Step 2: Create only if not exists
        if not existing:
            execution_repo.create_execution(
                underwriting_id="uw_001",
                underwriting_processor_id="up_789",
                organization_id="org_456",
                processor_name="p_bank_statement",
                payload={"test": "data"},
                payload_hash=payload_hash,
            )

    def test_active_executions_for_consolidation_pattern(self, execution_repo):
        """Test the pattern for retrieving active executions for consolidation."""
        # This is the key pattern for consolidation phase
        active_executions = execution_repo.get_active_executions("up_789")

        assert isinstance(active_executions, list)
        # In real implementation, would contain only enabled, completed executions
        # that are in current_executions_list
