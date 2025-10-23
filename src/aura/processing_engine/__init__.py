"""
Processing Engine Module

Core processor execution framework with 3-phase pipeline:
- Pre-extraction: Input validation and transformation
- Extraction: Factor extraction from validated inputs
- Post-extraction: Result validation and persistence

Architecture:
- services/ - Business logic services (filtration, execution, consolidation)
- utils/ - Utility functions (payload formatting, hashing)
- processors/ - Individual processor implementations
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
from .services import (
    Orchestrator,
    create_orchestrator,
    filtration,
    prepare_processor,
    generate_execution,
    execution,
    run_single_execution,
    consolidation,
)
from .utils import (
    generate_payload_hash,
    format_payload_list,
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
    # Services (Orchestrator class + plain functions)
    "Orchestrator",
    "create_orchestrator",
    "filtration",
    "prepare_processor",
    "generate_execution",
    "execution",
    "run_single_execution",
    "consolidation",
    # Utils
    "generate_payload_hash",
    "format_payload_list",
]
