"""
Execution Service

Plain functions for processor execution including parallel execution,
status tracking, and result persistence.
"""

import concurrent.futures
from datetime import datetime
from typing import Any, Optional

from ..repositories import (
    ProcessorRepository,
    ExecutionRepository,
    TestWorkflowRepository,
)
from .registry import get_registry
from ..models import ExecutionPayload


def execution(
    execution_list: list[str],
    processor_repo: ProcessorRepository,
    execution_repo: ExecutionRepository,
    test_workflow_repo: Optional[TestWorkflowRepository] = None,
) -> dict[str, Any]:
    """
    Execute multiple processor executions in parallel.

    Steps:
    1. For each execution, check if status is pending
    2. If pending, execute in parallel thread
    3. Wait for all executions to complete
    4. Return results

    Args:
        execution_list: List of execution IDs to run
        processor_repo: Repository for processor configuration
        execution_repo: Repository for execution management
        processor_registry: Registry of processor classes
        test_workflow_repo: Optional repository for test workflow tracking

    Returns:
        Execution results with counts and details
    """
    if not execution_list:
        return {"completed": 0, "failed": 0, "results": []}

    results = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = []

        for execution_id in execution_list:
            exec_data = execution_repo.get_execution_by_id(execution_id)

            if not exec_data:
                print(f"    ⚠️  Execution not found: {execution_id}")
                continue

            if exec_data["status"] in ["pending", "failed"]:
                print(f"    Launching: {exec_data['processor']}")
                future = executor.submit(
                    run_single_execution,
                    execution=exec_data,
                    processor_repo=processor_repo,
                    execution_repo=execution_repo,
                    test_workflow_repo=test_workflow_repo,
                )
                futures.append(future)

        for future in concurrent.futures.as_completed(futures):
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                print(f"    ❌ Execution error: {e}")
                results.append({"success": False, "error": str(e)})
    completed = sum(1 for r in results if r.get("success"))
    failed = sum(1 for r in results if not r.get("success"))

    return {"completed": completed, "failed": failed, "results": results}


def run_single_execution(
    execution: dict[str, Any],
    processor_repo: ProcessorRepository,
    execution_repo: ExecutionRepository,
    test_workflow_repo: Optional[TestWorkflowRepository] = None,
) -> dict[str, Any]:
    """
    Run a single processor execution.

    Args:
        execution: Execution record with processor, payload, etc.
        processor_repo: Repository for processor configuration
        execution_repo: Repository for execution management
        test_workflow_repo: Optional repository for test workflow tracking

    Returns:
        Execution result
    """
    step_start = datetime.now()
    execution_id = execution["id"]
    processor_name = execution["processor"]
    underwriting_processor_id = execution["underwriting_processor_id"]
    underwriting_id = execution["underwriting_id"]

    print(f"    Running: {processor_name}")

    try:
        execution_repo.update_execution_status(
            execution_id=execution_id, status="running", started_at=datetime.now()
        )

        processor_registry = get_registry()
        if not processor_registry.is_processor_registered(processor_name):
            raise Exception(f"Processor not registered: {processor_name}")

        processor_class = processor_registry.get_processor_class(processor_name)
        processor = processor_class(processor_repo=processor_repo)
        processor._underwriting_processor_id = underwriting_processor_id

        payload_data = execution["payload"]

        if isinstance(payload_data, dict):
            exec_payload = ExecutionPayload(
                underwriting_id=execution["underwriting_id"],
                underwriting_processor_id=underwriting_processor_id,
                application_form=payload_data.get("application_form", {}),
                owners_list=payload_data.get("owners_list", []),
                documents_list=payload_data.get("documents_list", []),
                revision_ids=payload_data.get("revision_id"),
            )

            if "revision_id" in payload_data:
                exec_payload.revision_id = payload_data["revision_id"]
        else:
            exec_payload = payload_data

        result = processor.execute(
            execution_id=execution_id,
            underwriting_processor_id=underwriting_processor_id,
            payload=exec_payload,
        )

        if result.is_successful():
            execution_repo.save_execution_result(
                execution_id=execution_id,
                output=result.output,
                factors={},
                cost_cents=int(result.total_cost_cents),
                completed_at=datetime.now(),
            )

            print(f"    ✅ Completed: {processor_name}")

            step_time = int((datetime.now() - step_start).total_seconds() * 1000)
            if test_workflow_repo:
                test_workflow_repo.log_stage(
                    underwriting_id=underwriting_id,
                    workflow_name="Workflow 1",
                    stage="run_execution",
                    payload={
                        "execution_id": execution_id,
                        "processor": processor_name,
                        "underwriting_processor_id": underwriting_processor_id,
                    },
                    input={"execution_payload": execution["payload"]},
                    output={
                        "result": "success",
                        "output": result.output,
                        "cost_cents": int(result.total_cost_cents),
                    },
                    status="completed",
                    execution_time_ms=step_time,
                    metadata={
                        "processor": processor_name,
                        "payload_hash": execution.get("payload_hash"),
                    },
                )

            return {
                "success": True,
                "execution_id": execution_id,
                "processor": processor_name,
                "output": result.output,
            }
        else:
            execution_repo.update_execution_status(
                execution_id=execution_id,
                status="failed",
                completed_at=datetime.now(),
                failed_reason=result.error_message,
            )

            print(f"    ❌ Failed: {processor_name} - {result.error_message}")

            step_time = int((datetime.now() - step_start).total_seconds() * 1000)
            if test_workflow_repo:
                test_workflow_repo.log_stage(
                    underwriting_id=underwriting_id,
                    workflow_name="Workflow 1",
                    stage="run_execution",
                    payload={
                        "execution_id": execution_id,
                        "processor": processor_name,
                        "underwriting_processor_id": underwriting_processor_id,
                    },
                    input={"execution_payload": execution["payload"]},
                    output={"result": "failed", "error": result.error_message},
                    status="failed",
                    execution_time_ms=step_time,
                    error_message=result.error_message,
                    metadata={
                        "processor": processor_name,
                        "payload_hash": execution.get("payload_hash"),
                    },
                )

            return {
                "success": False,
                "execution_id": execution_id,
                "processor": processor_name,
                "error": result.error_message,
            }

    except Exception as e:
        execution_repo.update_execution_status(
            execution_id=execution_id,
            status="failed",
            completed_at=datetime.now(),
            failed_reason=str(e),
        )

        print(f"      ❌ Exception: {execution_id} - {e}")

        step_time = int((datetime.now() - step_start).total_seconds() * 1000)
        if test_workflow_repo:
            test_workflow_repo.log_stage(
                underwriting_id=underwriting_id,
                workflow_name="Workflow 1",
                stage="run_execution",
                payload={
                    "execution_id": execution_id,
                    "processor": processor_name,
                    "underwriting_processor_id": underwriting_processor_id,
                },
                input={"execution_payload": execution["payload"]},
                output={"result": "exception", "error": str(e)},
                status="failed",
                execution_time_ms=step_time,
                error_message=str(e),
                metadata={
                    "processor": processor_name,
                    "exception_type": type(e).__name__,
                    "payload_hash": execution.get("payload_hash"),
                },
            )

        return {
            "success": False,
            "execution_id": execution_id,
            "processor": processor_name,
            "error": str(e),
        }
