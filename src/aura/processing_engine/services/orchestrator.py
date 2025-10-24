"""
Orchestrator Service

Main orchestration service that coordinates processor execution workflows.
"""

from datetime import datetime
from typing import Any, Optional

from ..repositories import (
    ProcessorRepository,
    ExecutionRepository,
    UnderwritingRepository,
)
from ..base_processor import BaseProcessor
from .filtration import filtration
from .execution import execution
from .consolidation import consolidation
from .registry import get_registry


class Orchestrator:
    """
    Main orchestration service for processor execution workflows.

    Coordinates the complete lifecycle of processor execution from event reception
    through filtration, execution, and consolidation.
    """

    def __init__(
        self,
        processor_repo: ProcessorRepository,
        execution_repo: ExecutionRepository,
        underwriting_repo: UnderwritingRepository,
    ):
        """
        Initialize orchestrator with repositories.

        Args:
            processor_repo: Repository for processor configuration
            execution_repo: Repository for execution management
            underwriting_repo: Repository for underwriting data
        """
        self.processor_repo = processor_repo
        self.execution_repo = execution_repo
        self.underwriting_repo = underwriting_repo

    def register_processor(self, processor_class: type[BaseProcessor]):
        """
        Register a processor class for orchestration.

        Args:
            processor_class: Processor class to instantiate (must have PROCESSOR_NAME)
        """
        get_registry().register_processor(processor_class)

    def handle_workflow1(self, underwriting_id: str) -> dict[str, Any]:
        """
        Handle Workflow 1: Automatic processor execution.

        Triggered by: underwriting.updated or document.analyzed events

        Steps:
        1. Filtration - Determine which processors should run
        2. Execution - Run pending processor executions in parallel
        3. Consolidation - Aggregate results and calculate factors

        Args:
            underwriting_id: The underwriting ID to process

        Returns:
            Workflow execution results with counts and details
        """
        print(f"\n{'='*70}")
        print("WORKFLOW 1: Automatic Execution")
        print(f"Underwriting ID: {underwriting_id}")
        print(f"{'='*70}\n")

        print("Step 1: Filtration")
        print("-" * 70)
        filtration_start = datetime.now()

        filtration_result = filtration(
            underwriting_id=underwriting_id,
        )
        filtration_time = int(
            (datetime.now() - filtration_start).total_seconds() * 1000
        )

        processor_list = filtration_result["processor_list"]
        execution_list = filtration_result["execution_list"]

        print(f"  Processors selected: {len(processor_list)}")
        print(f"  Executions to run: {len(execution_list)}")
        print()

        if not processor_list:
            print("  ℹ️  No processors matched triggers")
            return {
                "success": True,
                "processors_selected": 0,
                "executions_run": 0,
                "executions_failed": 0,
                "processors_consolidated": 0,
                "message": "No processors matched triggers",
                "details": {
                    "processor_list": [],
                    "execution_results": [],
                    "consolidation_results": [],
                },
            }

        print("Step 2: Execution")
        print("-" * 70)
        execution_start = datetime.now()
        execution_result = execution(
            execution_list=execution_list,
        )
        execution_time = int((datetime.now() - execution_start).total_seconds() * 1000)

        print(f"  Executions completed: {execution_result['completed']}")
        print(f"  Executions failed: {execution_result['failed']}")
        print()

        print("Step 3: Consolidation")
        print("-" * 70)
        consolidation_start = datetime.now()
        consolidation_result = consolidation(
            processor_list=processor_list,
        )
        consolidation_time = int(
            (datetime.now() - consolidation_start).total_seconds() * 1000
        )

        print(f"  Processors consolidated: {consolidation_result['consolidated']}")
        print()

        print("=" * 70)
        print("Workflow 1 Complete")
        print("=" * 70)
        print()

        return {
            "success": True,
            "processors_selected": len(processor_list),
            "executions_run": execution_result["completed"],
            "executions_failed": execution_result["failed"],
            "processors_consolidated": consolidation_result["consolidated"],
            "details": {
                "processor_list": processor_list,
                "execution_results": execution_result["results"],
                "consolidation_results": consolidation_result["results"],
            },
        }


def create_orchestrator(
    db_connection: Any
) -> Orchestrator:
    """
    Create orchestrator with initialized repositories.

    Args:
        db_connection: Database connection

    Returns:
        Configured Orchestrator instance
    """
    processor_repo = ProcessorRepository()
    processor_repo.__init__(db_connection)

    execution_repo = ExecutionRepository()
    execution_repo.__init__(db_connection)

    underwriting_repo = UnderwritingRepository()
    underwriting_repo.__init__(db_connection)

    return Orchestrator(
        processor_repo=processor_repo,
        execution_repo=execution_repo,
        underwriting_repo=underwriting_repo,
    )
