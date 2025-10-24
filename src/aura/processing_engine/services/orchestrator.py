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

    def handle_workflow2(self, underwriting_processor_id: str, execution_id: str = None, duplicate: bool = False, application_form: dict = None, document_list: list = None) -> dict[str, Any]:
        """
        Handle Workflow 2: Manual processor execution.

        Triggered by: underwriting.processor.execute events

        Scenarios:
        1. Rerun specific execution (with execution_id)
        2. Rerun entire processor (no execution_id)
        3. Run with selective data (application_form or document_list)

        Args:
            underwriting_processor_id: The underwriting processor to execute
            execution_id: Optional specific execution to rerun (Scenario 1)
            duplicate: Allow duplicate execution even with same hash
            application_form: Optional application form data (Scenario 3)
            document_list: Optional document list (Scenario 3)

        Returns:
            Execution results
        """
        print(f"\n{'='*70}")
        print("WORKFLOW 2: Manual Processor Execution")
        print(f"Underwriting Processor ID: {underwriting_processor_id}")
        if execution_id:
            print(f"Execution ID: {execution_id}")
        if duplicate:
            print("Duplicate: True")
        print(f"{'='*70}\n")

        results = {
            "success": False,
            "scenario": "unknown",
            "executions_run": 0,
            "executions_failed": 0,
            "processors_consolidated": 0,
            "details": {},
        }

        try:
            # Get processor configuration
            processor_config = self.processor_repo.get_underwriting_processor_by_id(
                underwriting_processor_id
            )
            if not processor_config:
                raise ValueError(f"Underwriting processor not found: {underwriting_processor_id}")

            underwriting_id = processor_config["underwriting_id"]
            underwriting_data = self.underwriting_repo.get_underwriting_with_details(underwriting_id)
            if not underwriting_data:
                raise ValueError(f"Underwriting not found: {underwriting_id}")

            execution_list_to_run = []
            processor_list_to_consolidate = [underwriting_processor_id]

            if execution_id:
                # Scenario 1: Rerun specific execution
                results["scenario"] = "Scenario 1: Rerun specific execution"
                existing_execution = self.execution_repo.get_execution_by_id(execution_id)
                if not existing_execution:
                    raise ValueError(f"Execution not found: {execution_id}")

                # If duplicate is true, create a new execution with the same payload
                if duplicate:
                    new_execution_id = self.execution_repo.create_execution(
                        underwriting_id=existing_execution["underwriting_id"],
                        underwriting_processor_id=existing_execution["underwriting_processor_id"],
                        organization_id=existing_execution["organization_id"],
                        processor_name=existing_execution["processor"],
                        payload=existing_execution["payload"],
                        payload_hash=existing_execution["payload_hash"]
                    )
                    execution_list_to_run.append(new_execution_id)
                    # Mark the old execution as superseded
                    self.execution_repo.mark_execution_superseded(existing_execution["id"], new_execution_id)
                    print(f"    🔄 EXECUTION SUPERSEDED (Scenario 1)")
                    print(f"        OLD EXECUTION: {existing_execution['id']}")
                    print(f"        NEW EXECUTION: {new_execution_id}")
                else:
                    execution_list_to_run.append(execution_id)
                    # Ensure the execution is marked as pending/failed to be rerun
                    self.execution_repo.update_execution_status(execution_id, status="pending")

            elif application_form or document_list:
                # Scenario 3: Selective data execution
                results["scenario"] = "Scenario 3: Selective data execution"
                # Construct a temporary payload for this specific run
                temp_payload = {
                    "underwriting_id": underwriting_id,
                    "underwriting_processor_id": underwriting_processor_id,
                    "application_form": application_form if application_form else underwriting_data.get("application_form", {}),
                    "owners_list": underwriting_data.get("owners", []),
                    "documents_list": document_list if document_list else underwriting_data.get("documents", []),
                }
                # Generate a new execution based on this selective data
                from .filtration import generate_execution
                from ..models import ExecutionPayload
                new_execution_id = generate_execution(
                    underwriting_processor_id=underwriting_processor_id,
                    payload=ExecutionPayload(**temp_payload),
                    processor_config=processor_config,
                    processor_triggers=self.processor_repo.get_processor_triggers(processor_config["processor"]),
                    duplicate=duplicate,
                )
                execution_list_to_run.append(new_execution_id)

            else:
                # Scenario 2: Rerun entire processor
                results["scenario"] = "Scenario 2: Rerun entire processor"
                # If duplicate=True, get current active executions BEFORE creating new ones
                current_executions = []
                if duplicate:
                    current_executions = self.execution_repo.get_active_executions(underwriting_processor_id)

                # Use prepare_processor to get all relevant executions for this processor
                from .filtration import prepare_processor
                prepared_executions = prepare_processor(
                    underwriting_processor_id=underwriting_processor_id,
                    underwriting_data=underwriting_data,
                    processor_config=processor_config,
                    duplicate=duplicate,
                )
                if prepared_executions is not None:
                    execution_list_to_run.extend(prepared_executions)

                    # If duplicate=True, supersede old executions with matching payload hash
                    if duplicate and current_executions and prepared_executions:
                        for new_exec_id in prepared_executions:
                            new_exec = self.execution_repo.get_execution_by_id(new_exec_id)
                            if new_exec and new_exec.get('payload_hash'):
                                new_payload_hash = new_exec['payload_hash']

                                # Find old execution with same payload hash
                                for old_exec in current_executions:
                                    if old_exec.get('payload_hash') == new_payload_hash:
                                        self.execution_repo.mark_execution_superseded(old_exec['id'], new_exec_id)
                                        print(f"    🔄 EXECUTION SUPERSEDED (Scenario 2)")
                                        print(f"        OLD EXECUTION: {old_exec['id']}")
                                        print(f"        NEW EXECUTION: {new_exec_id}")
                                        break  # Only supersede the first match

            if not execution_list_to_run:
                results["message"] = "No new executions to run."
                results["success"] = True
                return results

            # Step 2: Execution
            execution_result = execution(
                execution_list=execution_list_to_run,
            )
            results["executions_run"] = execution_result["completed"]
            results["executions_failed"] = execution_result["failed"]
            results["details"]["execution_results"] = execution_result["results"]

            # Step 3: Consolidation
            consolidation_result = consolidation(
                processor_list=processor_list_to_consolidate,
            )
            results["processors_consolidated"] = consolidation_result["consolidated"]
            results["details"]["consolidation_results"] = consolidation_result["results"]

            results["success"] = True

        except Exception as e:
            results["success"] = False
            results["error"] = str(e)
            print(f"❌ Workflow 2 Error: {str(e)}")
            import traceback
            traceback.print_exc()

        print("=" * 70)
        print("Workflow 2 Complete")
        print("=" * 70)
        print()

        return {
            "success": results.get("success", True),
            "scenario": results.get("scenario", "unknown"),
            "details": results,
        }

    def handle_workflow3(self, underwriting_processor_id: str) -> dict[str, Any]:
        """
        Handle Workflow 3: Processor consolidation only.

        Triggered by: underwriting.processor.consolidation events

        Steps:
        1. Load current active executions for the processor
        2. Re-consolidate factors from active executions (no new executions)
        3. Update factors in database

        Args:
            underwriting_processor_id: The underwriting processor to consolidate

        Returns:
            Consolidation results
        """
        print(f"\n{'='*70}")
        print("WORKFLOW 3: Consolidation Only")
        print(f"Underwriting Processor ID: {underwriting_processor_id}")
        print(f"{'='*70}\n")

        results = {
            "success": False,
            "processors_consolidated": 0,
            "details": {},
        }

        try:
            processor_config = self.processor_repo.get_underwriting_processor_by_id(
                underwriting_processor_id
            )
            if not processor_config:
                raise ValueError(f"Underwriting processor not found: {underwriting_processor_id}")

            underwriting_id = processor_config["underwriting_id"]
            processor_list_to_consolidate = [underwriting_processor_id]

            # Step 1: Consolidation
            consolidation_result = consolidation(
                processor_list=processor_list_to_consolidate,
            )
            results["processors_consolidated"] = consolidation_result["consolidated"]
            results["details"]["consolidation_results"] = consolidation_result["results"]

            results["success"] = True

        except Exception as e:
            results["success"] = False
            results["error"] = str(e)

        print("=" * 70)
        print("Workflow 3 Complete")
        print("=" * 70)
        print()

        return {
            "success": results.get("success", True),
            "details": results,
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
