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
)
from .registry import get_registry
from ..models import ExecutionPayload


def execution(
    execution_list: list[str],
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

    Returns:
        Execution results with counts and details
    """
    if not execution_list:
        return {"completed": 0, "failed": 0, "results": []}

    print(f"    🚀 Starting execution of {len(execution_list)} executions")
    print(f"    📋 Execution IDs: {execution_list}")

    # Instantiate repositories directly
    execution_repo = ExecutionRepository()

    results = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = []

        for execution_id in execution_list:
            exec_data = execution_repo.get_execution_by_id(execution_id)

            if not exec_data:
                print(f"    ⚠️  Execution not found: {execution_id}")
                continue

            if exec_data["status"] in ["pending", "failed"]:
                print(f"    🎯 Launching: {exec_data['processor']} (ID: {execution_id}, Status: {exec_data['status']})")
                future = executor.submit(
                    run_execution,
                    execution=exec_data,
                )
                futures.append(future)
            else:
                print(f"    ⏭️  Skipping: {exec_data['processor']} (ID: {execution_id}, Status: {exec_data['status']})")

        print(f"    ⏳ Waiting for {len(futures)} executions to complete...")
        
        for future in concurrent.futures.as_completed(futures):
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                print(f"    ❌ Execution error: {e}")
                results.append({"success": False, "error": str(e)})
    
    completed = sum(1 for r in results if r.get("success"))
    failed = sum(1 for r in results if not r.get("success"))
    
    print(f"    📊 Execution Summary: {completed} completed, {failed} failed")
    
    return {"completed": completed, "failed": failed, "results": results}


def run_execution(
    execution: dict[str, Any],
) -> dict[str, Any]:
    """
    Run a single processor execution.

    Args:
        execution: Execution record with processor, payload, etc.

    Returns:
        Execution result
    """
    # Instantiate repositories directly
    execution_repo = ExecutionRepository()
    processor_repo = ProcessorRepository()

    step_start = datetime.now()
    execution_id = execution["id"]
    processor_name = execution["processor"]
    underwriting_processor_id = execution["underwriting_processor_id"]
    underwriting_id = execution["underwriting_id"]

    print(f"    🔄 Running: {processor_name} (Execution: {execution_id[:8]}...)")
    print(f"        📍 Underwriting: {underwriting_id}")
    print(f"        🔗 Processor ID: {underwriting_processor_id}")

    try:
        execution_repo.update_execution_status(
            execution_id=execution_id, status="running", started_at=datetime.now()
        )

        processor_registry = get_registry()
        if not processor_registry.is_processor_registered(processor_name):
            raise Exception(f"Processor not registered: {processor_name}")

        processor_class = processor_registry.get_processor(processor_name)
        processor = processor_class(processor_repo=processor_repo)
        processor._underwriting_processor_id = underwriting_processor_id

        payload_data = execution["payload"]
        
        # Log payload information
        if isinstance(payload_data, dict):
            app_form_keys = list(payload_data.get("application_form", {}).keys())
            docs_count = len(payload_data.get("documents_list", []))
            owners_count = len(payload_data.get("owners_list", []))
            print(f"        📦 Payload: {len(app_form_keys)} app fields, {docs_count} docs, {owners_count} owners")
            
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
            print(f"        📦 Payload: {type(payload_data).__name__}")
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

            duration = (datetime.now() - step_start).total_seconds()
            output_keys = list(result.output.keys()) if isinstance(result.output, dict) else "N/A"
            cost_dollars = result.total_cost_cents / 100 if result.total_cost_cents else 0
            
            print(f"    ✅ Completed: {processor_name} ({duration:.2f}s, ${cost_dollars:.2f})")
            print(f"        📊 Output: {len(output_keys) if isinstance(output_keys, list) else 'N/A'} factors")

            return {
                "success": True,
                "execution_id": execution_id,
                "processor": processor_name,
                "output": result.output,
                "duration_seconds": duration,
                "cost_cents": result.total_cost_cents,
            }
        else:
            execution_repo.update_execution_status(
                execution_id=execution_id,
                status="failed",
                completed_at=datetime.now(),
                failed_reason=result.error_message,
            )

            duration = (datetime.now() - step_start).total_seconds()
            print(f"    ❌ Failed: {processor_name} ({duration:.2f}s)")
            print(f"        💥 Error: {result.error_message}")

            return {
                "success": False,
                "execution_id": execution_id,
                "processor": processor_name,
                "error": result.error_message,
                "duration_seconds": duration,
            }

    except Exception as e:
        execution_repo.update_execution_status(
            execution_id=execution_id,
            status="failed",
            completed_at=datetime.now(),
            failed_reason=str(e),
        )

        duration = (datetime.now() - step_start).total_seconds()
        print(f"    💥 Exception: {processor_name} ({duration:.2f}s)")
        print(f"        🔥 Error: {str(e)}")

        return {
            "success": False,
            "execution_id": execution_id,
            "processor": processor_name,
            "error": str(e),
            "duration_seconds": duration,
        }
