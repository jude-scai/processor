"""
Filtration Service

Plain functions for processor filtration, selection, and execution generation.
"""

from typing import Any, Optional

from ..repositories import (
    UnderwritingRepository,
    ProcessorRepository,
    ExecutionRepository,
    TestWorkflowRepository,
)
from ..utils.payload import format_payload_list as format_payload_list_util
from ..utils.hashing import generate_payload_hash
from .registry import get_registry


def filtration(
    underwriting_id: str,
) -> dict[str, Any]:
    """
    Filter and select processors that should run.

    Steps:
    1. Get underwriting data
    2. Get processors (enabled=true, auto=true)
    3. For each processor, call prepare_processor
    4. Build processor_list and execution_list

    Args:
        underwriting_id: The underwriting ID

    Returns:
        Dictionary with processor_list, execution_list, and eligible_processors
    """
    processor_repo = ProcessorRepository()
    underwriting_repo = UnderwritingRepository()

    underwriting = underwriting_repo.get_underwriting_with_details(underwriting_id)

    if not underwriting:
        print(f"  ⚠️  Underwriting not found: {underwriting_id}")
        return {"processor_list": [], "execution_list": [], "eligible_processors": []}

    processors = processor_repo.get_underwriting_processors(
        underwriting_id=underwriting_id, enabled_only=True, auto_only=True
    )

    print(f"  Found {len(processors)} eligible processors")

    processor_list = []
    execution_list = []

    for processor_config in processors:
        print(f"  Checking processor: {processor_config['processor']}")

        preparation = prepare_processor(
            underwriting_processor_id=processor_config["id"],
            underwriting_data=underwriting,
            processor_config=processor_config,
        )

        if preparation is None:
            print("    ℹ️  No triggers matched - skipped")
        elif isinstance(preparation, list):
            if len(preparation) == 0:
                skipped_count = len(processor_config.get("current_executions_list", []))
                print("    ✅ Triggers matched, no new executions needed")
                if skipped_count > 0:
                    print(
                        f"       Skipped {skipped_count} existing execution(s) (already completed)"
                    )
            else:
                print(
                    f"    ✅ Triggers matched, {len(preparation)} new execution(s)"
                )

            processor_list.append(processor_config["id"])
            execution_list.extend(preparation)
    return {
        "processor_list": processor_list,
        "execution_list": execution_list,
        "eligible_processors": processors,
    }


def prepare_processor(
    underwriting_processor_id: str,
    underwriting_data: dict[str, Any],
    processor_config: dict[str, Any],
    duplicate: bool = False,
) -> Optional[list[str]]:
    """
    Preparation: Determine if processor should participate.

    Steps:
    1. Format payload list (based on processor type)
    2. For each payload, generate execution
    3. Compare with current executions
    4. Return new executions or NULL

    Args:
        underwriting_processor_id: The underwriting processor ID
        underwriting_data: Complete underwriting data
        processor_config: Processor configuration dict
        duplicate: Allow duplicate executions

    Returns:
        List of execution IDs to run, empty list if triggers matched but no new executions,
        or None if no triggers matched
    """
    test_workflow_repo = TestWorkflowRepository()

    registry = get_registry()
    processor_class = registry.get_processor(processor_config["processor"])
    payload_list = format_payload_list_util(
        processor_type=processor_class.PROCESSOR_TYPE,
        processor_triggers=processor_class.PROCESSOR_TRIGGERS,
        underwriting_data=underwriting_data,
    )

    if not payload_list:
        return None

    execution_list = [
        generate_execution(
            underwriting_processor_id=underwriting_processor_id,
            payload=payload,
            processor_config=processor_config,
            processor_triggers=processor_class.PROCESSOR_TRIGGERS,
            duplicate=duplicate,
        )
        for payload in payload_list
    ]

    current_executions = ExecutionRepository().get_active_executions(
        underwriting_processor_id
    )

    current_execution_ids = [ex["id"] for ex in current_executions]

    new_exe_list = [eid for eid in execution_list if eid not in current_execution_ids]
    del_exe_list = [eid for eid in current_execution_ids if eid not in execution_list]

    if not new_exe_list and not del_exe_list:
        return []

    ProcessorRepository().update_current_executions_list(
        underwriting_processor_id=underwriting_processor_id,
        execution_ids=execution_list,
    )

    test_workflow_repo.log_stage(
        underwriting_id=underwriting_data.get("id"),
        workflow_name="Workflow 1",
        stage="filtration (prepare_processor)",
        payload={
            "underwriting_processor_id": underwriting_processor_id,
            "processor_name": processor_config["processor"],
            "duplicate": duplicate,
        },
        input={
            "processor_config": {
                "processor": processor_config["processor"],
                "enabled": processor_config.get("enabled"),
                "auto": processor_config.get("auto"),
            },
            "payload_list": payload_list,
        },
        output={
            "new_executions": new_exe_list,
            "deleted_executions": del_exe_list,
        },
        status="completed",
    )

    return new_exe_list


def generate_execution(
    underwriting_processor_id: str,
    payload: dict[str, Any],
    processor_config: dict[str, Any],
    processor_triggers: dict[str, list[str]],
    duplicate: bool = False,
) -> str:
    """
    Generate execution: Create or reuse execution based on payload hash.

    Steps:
    1. Generate hash from payload (only trigger fields are hashed)
    2. Find existing execution with same hash
    3. If exists and not duplicate: return existing ID
    4. If exists and duplicate: create new with link
    5. If not exists: create new

    Args:
        underwriting_processor_id: The underwriting processor ID
        payload: Execution payload (full payload stored, but only triggers hashed)
        processor_config: Processor configuration with underwriting_id, organization_id, processor name
        processor_triggers: Processor triggers to determine which fields to hash
        duplicate: Allow creating duplicate execution

    Returns:
        Execution ID (new or existing)
    """
    execution_repo = ExecutionRepository()
    test_workflow_repo = TestWorkflowRepository()

    payload_hash = generate_payload_hash(payload, processor_triggers)

    existing = execution_repo.find_execution_by_hash(
        underwriting_processor_id, payload_hash
    )

    if existing and not duplicate:
        execution_id = existing["id"]
        test_workflow_repo.log_stage(
            underwriting_id=processor_config.get("underwriting_id"),
            workflow_name="Workflow 1",
            stage="filtration (generate_execution)",
            payload={
                "underwriting_processor_id": underwriting_processor_id,
                "payload": payload,
                "duplicate": duplicate,
            },
            input={
                "payload_hash": payload_hash,
                "processor_config": processor_config,
            },
            output={
                "execution_id": execution_id,
                "action": "reused_existing",
            },
            status="completed",
        )
        return execution_id

    execution_id = execution_repo.create_execution(
        underwriting_id=processor_config.get(
            "underwriting_id", "placeholder_underwriting_id"
        ),
        underwriting_processor_id=underwriting_processor_id,
        organization_id=processor_config.get(
            "organization_id", "placeholder_organization_id"
        ),
        processor_name=processor_config.get("processor", "placeholder_processor_name"),
        payload=payload,
        payload_hash=payload_hash,
    )

    test_workflow_repo.log_stage(
        underwriting_id=processor_config.get("underwriting_id"),
        workflow_name="Workflow 1",
        stage="filtration (generate_execution)",
        payload={
            "underwriting_processor_id": underwriting_processor_id,
            "payload": payload,
            "duplicate": duplicate,
        },
        input={
            "payload_hash": payload_hash,
            "processor_config": processor_config,
        },
        output={
            "execution_id": execution_id,
            "action": "created_new",
        },
        status="completed",
    )

    return execution_id
