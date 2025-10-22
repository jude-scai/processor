"""
Processing Engine Module

Core processor execution framework with 3-phase pipeline:
- Pre-extraction: Input validation and transformation
- Extraction: Factor extraction from validated inputs
- Post-extraction: Result validation and persistence
"""

from .base_processor import BaseProcessor
from .exceptions import (
    ProcessorException,
    PrevalidationError,
    InputValidationError,
    TransformationError,
    FactorExtractionError,
    DataTransformationError,
    ApiError,
    ResultValidationError,
    PersistenceError,
    ConfigurationError,
)
from .models import (
    ProcessingResult,
    ExecutionStatus,
    ProcessorType,
    ProcessorConfig,
    ExecutionPayload,
    ValidationResult,
)

__all__ = [
    # Base class
    "BaseProcessor",

    # Exceptions
    "ProcessorException",
    "PrevalidationError",
    "InputValidationError",
    "TransformationError",
    "FactorExtractionError",
    "DataTransformationError",
    "ApiError",
    "ResultValidationError",
    "PersistenceError",
    "ConfigurationError",

    # Models
    "ProcessingResult",
    "ExecutionStatus",
    "ProcessorType",
    "ProcessorConfig",
    "ExecutionPayload",
    "ValidationResult",
]

