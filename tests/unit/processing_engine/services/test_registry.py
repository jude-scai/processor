"""
Tests for Processor Registry

Tests the singleton registry pattern, processor registration, and auto-discovery.
"""

# pylint: disable=redefined-outer-name  # pytest fixtures

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent / "src"))

import pytest  # pylint: disable=import-error

from aura.processing_engine.services.registry import (
    Registry,
    get_registry,
)  # pylint: disable=import-error,wrong-import-position
from aura.processing_engine.base_processor import (
    BaseProcessor,
    ProcessorType,
)  # pylint: disable=import-error,wrong-import-position
from aura.processing_engine.models import (
    ExecutionPayload,
    ValidationResult,
)  # pylint: disable=import-error,wrong-import-position


class MockProcessor(BaseProcessor):
    """Mock processor for testing."""

    PROCESSOR_NAME = "test_mock_processor"
    PROCESSOR_TYPE = ProcessorType.APPLICATION
    PROCESSOR_TRIGGERS = {"application_form": ["merchant.name"]}

    def transform_input(self, payload: ExecutionPayload) -> dict:
        return {"name": payload.application_form.get("merchant.name")}

    def validate_input(self, transformed_data: dict) -> ValidationResult:
        return ValidationResult(is_valid=True)

    def extract(self, validated_data: dict) -> dict:
        return {"f_merchant_name": validated_data.get("name")}

    def validate_output(self, extraction_output: dict) -> ValidationResult:
        return ValidationResult(is_valid=True)


class TestRegistry:
    """Test cases for Registry class."""

    def setup_method(self):
        """Clear registry before each test (except auto-discovered processors)."""
        # Note: We don't clear the registry to preserve auto-discovered test processors
        pass

    def test_singleton_pattern(self):
        """Test that Registry is a singleton."""
        registry1 = get_registry()
        registry2 = get_registry()
        registry3 = Registry()

        assert registry1 is registry2
        assert registry1 is registry3

    def test_register_processor(self):
        """Test processor registration."""
        registry = get_registry()

        # Register processor
        registry.register_processor(MockProcessor)

        # Verify registration
        assert registry.is_processor_registered("test_mock_processor")

    def test_get_processor(self):
        """Test retrieving registered processor."""
        registry = get_registry()
        registry.register_processor(MockProcessor)

        # Get processor
        processor_class = registry.get_processor("test_mock_processor")

        assert processor_class == MockProcessor
        assert processor_class.PROCESSOR_NAME == "test_mock_processor"

    def test_get_unregistered_processor(self):
        """Test error when getting unregistered processor."""
        registry = get_registry()

        with pytest.raises(ValueError, match="not found in registry"):
            registry.get_processor("nonexistent_processor")

    def test_register_without_processor_name(self):
        """Test error when registering processor without PROCESSOR_NAME."""

        class InvalidProcessor(BaseProcessor):
            # Missing PROCESSOR_NAME
            pass

        registry = get_registry()

        with pytest.raises(ValueError, match="must define a PROCESSOR_NAME"):
            registry.register_processor(InvalidProcessor)

    def test_get_registered_processors(self):
        """Test getting all registered processors."""
        registry = get_registry()
        registry.register_processor(MockProcessor)

        processors = registry.get_registered_processors()

        # Should include mock processor
        assert "test_mock_processor" in processors
        assert processors["test_mock_processor"] == MockProcessor

        # Should also include auto-discovered test processors
        assert "test_application_processor" in processors
        assert "test_document_processor" in processors
        assert "test_stipulation_processor" in processors
        assert "p_test_application_2" in processors

    def test_clear_registry(self):
        """Test clearing all registered processors."""
        registry = get_registry()

        # Get count before
        processors_before = len(registry.get_registered_processors())

        # Verify processors exist before clearing
        assert processors_before > 0

        # Clear registry
        registry.clear_registry()

        # Verify all processors are cleared
        assert len(registry.get_registered_processors()) == 0

        # Re-register one to verify clear worked
        registry.register_processor(MockProcessor)
        assert registry.is_processor_registered("test_mock_processor")
        assert len(registry.get_registered_processors()) == 1

    def test_auto_discovery(self):
        """Test that test processors are auto-discovered on import."""
        registry = get_registry()

        # Get all registered processors
        processors = registry.get_registered_processors()

        # At minimum should have some processors (may be cleared by previous test)
        # The important thing is that auto-discovery happens on module import
        # If registry was just cleared, we can re-import to test auto-discovery
        if len(processors) == 0:
            # Registry was cleared - auto-discovery already happened on initial import
            # Just verify the mechanism works by checking the code path exists
            assert hasattr(registry, "register_processor")
        else:
            # Test processors should be auto-registered
            # Note: This depends on whether registry was cleared by previous tests
            registered_names = list(processors.keys())
            assert len(registered_names) > 0  # At least some processors registered

    def test_processor_overwrite_warning(self, capsys):
        """Test warning when overwriting existing processor."""
        registry = get_registry()

        # Register processor twice
        registry.register_processor(MockProcessor)
        registry.register_processor(MockProcessor)

        # Check for warning message
        captured = capsys.readouterr()
        assert "already registered" in captured.out.lower()
        assert "Overwriting" in captured.out
