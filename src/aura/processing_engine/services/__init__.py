"""
Processing Engine Services

Business logic services for processor orchestration, filtration, execution, and consolidation.

Services are implemented as plain functions for simplicity and testability.
"""

from .orchestrator import Orchestrator, create_orchestrator
from .filtration import filtration, prepare_processor, generate_execution
from .execution import execution
from .consolidation import consolidation
from .scheduler import UnderwritingScheduler, scheduler
from .registry import (
    Registry,
    get_registry,
)

__all__ = [
    "Orchestrator",
    "create_orchestrator",
    "filtration",
    "prepare_processor",
    "generate_execution",
    "execution",
    "consolidation",
    "UnderwritingScheduler",
    "scheduler",
    "Registry",
    "get_registry",
]
