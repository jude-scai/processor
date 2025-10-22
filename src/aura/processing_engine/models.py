"""
Processing Engine Data Models

Defines data structures for processor execution results and configuration.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class ExecutionStatus(str, Enum):
    """Execution status enumeration"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ProcessorType(str, Enum):
    """Processor type enumeration"""
    APPLICATION = "application"
    STIPULATION = "stipulation"
    DOCUMENT = "document"


@dataclass
class ProcessingResult:
    """
    Result of a processor execution.

    Contains execution status, outputs, costs, and error information.
    """

    # Execution identification
    execution_id: str
    processor_name: str
    underwriting_processor_id: str

    # Execution status
    status: ExecutionStatus

    # Timing information
    started_at: datetime
    completed_at: datetime | None = None
    duration_seconds: float | None = None

    # Results and outputs
    output: dict[str, Any] = field(default_factory=dict)

    # Cost tracking
    total_cost_cents: float = 0.0
    cost_breakdown: dict[str, float] = field(default_factory=dict)

    # Error information (if failed)
    error_message: str | None = None
    error_type: str | None = None
    error_phase: str | None = None  # pre-extraction, extraction, post-extraction

    # Input tracking
    input_hash: str | None = None
    document_revision_ids: list[str] = field(default_factory=list)
    document_ids_hash: str | None = None

    # Supersession tracking
    supersedes_execution_id: str | None = None
    superseded_by_execution_id: str | None = None

    def is_successful(self) -> bool:
        """Check if execution completed successfully"""
        return self.status == ExecutionStatus.COMPLETED

    def is_failed(self) -> bool:
        """Check if execution failed"""
        return self.status == ExecutionStatus.FAILED

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "execution_id": self.execution_id,
            "processor_name": self.processor_name,
            "underwriting_processor_id": self.underwriting_processor_id,
            "status": self.status.value,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": self.duration_seconds,
            "output": self.output,
            "total_cost_cents": self.total_cost_cents,
            "cost_breakdown": self.cost_breakdown,
            "error_message": self.error_message,
            "error_type": self.error_type,
            "error_phase": self.error_phase,
            "input_hash": self.input_hash,
            "document_revision_ids": self.document_revision_ids,
            "document_ids_hash": self.document_ids_hash,
            "supersedes_execution_id": self.supersedes_execution_id,
            "superseded_by_execution_id": self.superseded_by_execution_id,
        }


@dataclass
class ProcessorConfig:
    """
    Configuration for a processor instance.

    Combines default processor configuration with tenant-specific overrides.
    """

    processor_name: str
    processor_type: ProcessorType
    enabled: bool = True
    auto: bool = True

    # Configuration values
    config: dict[str, Any] = field(default_factory=dict)

    # Trigger configuration
    triggers: dict[str, list[str]] = field(default_factory=dict)

    # Priority for consolidation order
    priority: int = 0

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by key"""
        return self.config.get(key, default)

    def __getitem__(self, key: str) -> Any:
        """Allow dict-style access to config values"""
        return self.config[key]


@dataclass
class ExecutionPayload:
    """
    Input payload for processor execution.

    Contains all data needed to run a processor.
    """

    # Identification
    underwriting_id: str
    underwriting_processor_id: str

    # Application form data (flattened dot notation)
    application_form: dict[str, Any] = field(default_factory=dict)

    # Owners list (kept as array)
    owners_list: list[dict[str, Any]] = field(default_factory=list)

    # Documents list with metadata
    documents_list: list[dict[str, Any]] = field(default_factory=list)

    # Configuration for this execution
    config: dict[str, Any] = field(default_factory=dict)

    # Optional: specific document revisions for rerun
    revision_ids: list[str] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for hashing"""
        return {
            "underwriting_id": self.underwriting_id,
            "underwriting_processor_id": self.underwriting_processor_id,
            "application_form": self.application_form,
            "owners_list": self.owners_list,
            "documents_list": self.documents_list,
            "config": self.config,
            "revision_ids": self.revision_ids,
        }


@dataclass
class ValidationResult:
    """Result of input or output validation"""

    is_valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def add_error(self, error: str) -> None:
        """Add validation error"""
        self.errors.append(error)
        self.is_valid = False

    def add_warning(self, warning: str) -> None:
        """Add validation warning"""
        self.warnings.append(warning)

    def __bool__(self) -> bool:
        """Allow boolean evaluation"""
        return self.is_valid

