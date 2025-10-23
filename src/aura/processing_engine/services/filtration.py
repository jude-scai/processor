"""
Filtration Service

Plain functions for processor filtration, selection, and execution generation.
"""

from datetime import datetime
from typing import Any, Optional

from ..repositories import ProcessorRepository, ExecutionRepository, UnderwritingRepository, TestWorkflowRepository
from ..base_processor import BaseProcessor
from ..utils.payload import format_payload_list as format_payload_list_util
from ..utils.hashing import generate_payload_hash


def filtration(
    underwriting_id: str,
    processor_repo: ProcessorRepository,
    execution_repo: ExecutionRepository,
    underwriting_repo: UnderwritingRepository,
    processor_registry: dict[str, type[BaseProcessor]],
    test_workflow_repo: Optional[TestWorkflowRepository] = None
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
        processor_repo: Repository for processor configuration
        execution_repo: Repository for execution management
        underwriting_repo: Repository for underwriting data
        processor_registry: Registry of processor classes
        test_workflow_repo: Optional repository for test workflow tracking
        
    Returns:
        Dictionary with processor_list, execution_list, and eligible_processors
    """
    # Step 1: Get underwriting data
    underwriting = underwriting_repo.get_underwriting_with_details(underwriting_id)
    
    if not underwriting:
        print(f"  ⚠️  Underwriting not found: {underwriting_id}")
        return {"processor_list": [], "execution_list": [], "eligible_processors": []}
    
    # Step 2: Get processors (enabled=true, auto=true)
    processors = processor_repo.get_underwriting_processors(
        underwriting_id=underwriting_id,
        enabled_only=True,
        auto_only=True
    )
    
    print(f"  Found {len(processors)} eligible processors")
    
    processor_list = []
    execution_list = []
    
    # Step 3: Check each processor
    for processor_config in processors:
        underwriting_processor_id = processor_config['id']
        processor_name = processor_config['processor']
        
        print(f"  Checking processor: {processor_name}")
        
        # Call prepare_processor
        prepare_result = prepare_processor(
            underwriting_processor_id=underwriting_processor_id,
            underwriting_data=underwriting,
            processor_config=processor_config,
            processor_repo=processor_repo,
            execution_repo=execution_repo,
            processor_registry=processor_registry,
            test_workflow_repo=test_workflow_repo
        )
        
        # Check result
        if prepare_result is None:
            print(f"    ℹ️  No triggers matched - skipped")
        elif isinstance(prepare_result, list):
            if len(prepare_result) == 0:
                # Get skipped execution details from processor config
                skipped_count = len(processor_config.get('current_executions_list', []))
                print(f"    ✅ Triggers matched, no new executions needed")
                if skipped_count > 0:
                    print(f"       Skipped {skipped_count} existing execution(s) (already completed)")
            else:
                print(f"    ✅ Triggers matched, {len(prepare_result)} new execution(s)")
            
            # Add to processor_list (for consolidation)
            processor_list.append(underwriting_processor_id)
            
            # Add to execution_list (for execution)
            execution_list.extend(prepare_result)
    
    # Return results with eligible processors for orchestrator logging
    return {
        "processor_list": processor_list,
        "execution_list": execution_list,
        "eligible_processors": processors
    }


def prepare_processor(
    underwriting_processor_id: str,
    underwriting_data: dict[str, Any],
    processor_config: dict[str, Any],
    processor_repo: ProcessorRepository,
    execution_repo: ExecutionRepository,
    processor_registry: dict[str, type[BaseProcessor]],
    test_workflow_repo: Optional[TestWorkflowRepository] = None,
    duplicate: bool = False
) -> Optional[list[str]]:
    """
    Prepare processor: Determine if processor should participate.
    
    Steps:
    1. Format payload list (based on processor type)
    2. For each payload, generate execution
    3. Compare with current executions
    4. Return new executions or NULL
    
    Args:
        underwriting_processor_id: The underwriting processor ID
        underwriting_data: Complete underwriting data
        processor_config: Processor configuration dict
        processor_repo: Repository for processor configuration
        execution_repo: Repository for execution management
        processor_registry: Registry of processor classes
        test_workflow_repo: Optional repository for test workflow tracking
        duplicate: Allow duplicate executions
        
    Returns:
        List of execution IDs to run, empty list if triggers matched but no new executions,
        or None if no triggers matched
    """
    step_start = datetime.now()
    
    processor_name = processor_config['processor']
    
    # Get processor instance from registry
    if processor_name not in processor_registry:
        print(f"      ⚠️  Processor not registered: {processor_name}")
        return None
    
    processor_class = processor_registry[processor_name]
    
    # Format payload list using utility function
    format_start = datetime.now()
    payload_list = format_payload_list_util(
        processor_type=processor_class.PROCESSOR_TYPE,
        processor_triggers=processor_class.PROCESSOR_TRIGGERS,
        underwriting_data=underwriting_data
    )
    format_time = int((datetime.now() - format_start).total_seconds() * 1000)
    
    # Log format_payload_list with proper payload/input/output
    if test_workflow_repo:
        test_workflow_repo.log_stage(
            underwriting_id=underwriting_data.get('id'),
            workflow_name="Workflow 1",
            stage="format_payload_list",
            payload={
                "underwriting_processor_id": underwriting_processor_id,
                "processor_name": processor_name,
                "processor_type": str(processor_class.PROCESSOR_TYPE),
                "processor_triggers": processor_class.PROCESSOR_TRIGGERS
            },
            input={
                "underwriting_data_keys": list(underwriting_data.keys()),
                "merchant_fields": list(underwriting_data.get('merchant', {}).keys()) if underwriting_data.get('merchant') else [],
                "owners_count": len(underwriting_data.get('owners', []))
            },
            output={
                "payload_list": payload_list,
                "payload_count": len(payload_list) if payload_list else 0,
                "result": "NULL" if not payload_list else "OK"
            },
            status="completed",
            execution_time_ms=format_time,
            metadata={
                "triggers_matched": payload_list is not None and len(payload_list) > 0,
                "processor_type": str(processor_class.PROCESSOR_TYPE)
            }
        )
    
    if not payload_list:
        # No triggers matched or no data available
        return None
    
    # Generate executions for each payload
    execution_list = []
    for payload in payload_list:
        execution_id = generate_execution(
            underwriting_processor_id=underwriting_processor_id,
            payload=payload,
            processor_repo=processor_repo,
            execution_repo=execution_repo,
            test_workflow_repo=test_workflow_repo,
            duplicate=duplicate
        )
        execution_list.append(execution_id)
    
    # Get current executions for this processor
    current_executions = processor_config.get('current_executions_list', [])
    
    # Calculate new and deleted executions
    new_exe_list = [eid for eid in execution_list if eid not in current_executions]
    del_exe_list = [eid for eid in current_executions if eid not in execution_list]
    skipped_exe_list = [eid for eid in execution_list if eid in current_executions]
    
    # If both lists empty, no changes
    if not new_exe_list and not del_exe_list:
        # Log that executions were skipped (already exist and current)
        if test_workflow_repo and skipped_exe_list:
            step_time = int((datetime.now() - step_start).total_seconds() * 1000)
            test_workflow_repo.log_stage(
                underwriting_id=underwriting_data.get('id'),
                workflow_name="Workflow 1",
                stage="prepare_processor",
                payload={
                    "underwriting_processor_id": underwriting_processor_id,
                    "processor_name": processor_name,
                    "duplicate": duplicate
                },
                input={
                    "processor_config": {
                        "processor": processor_config['processor'],
                        "enabled": processor_config.get('enabled'),
                        "auto": processor_config.get('auto'),
                        "current_executions_list": processor_config.get('current_executions_list', [])
                    },
                    "payload_list": payload_list
                },
                output={
                    "execution_list": execution_list,
                    "new_executions": [],
                    "deleted_executions": [],
                    "skipped_executions": skipped_exe_list,
                    "result": "SKIPPED - All executions already exist and current"
                },
                status="completed",
                execution_time_ms=step_time,
                metadata={
                    "payloads_generated": len(payload_list),
                    "executions_total": len(execution_list),
                    "new_executions": 0,
                    "deleted_executions": 0,
                    "skipped_executions": len(skipped_exe_list)
                }
            )
        return None
    
    # Update current executions
    processor_repo.update_current_executions_list(
        underwriting_processor_id=underwriting_processor_id,
        execution_ids=execution_list
    )
    
    # Log prepare_processor with proper payload/input/output
    step_time = int((datetime.now() - step_start).total_seconds() * 1000)
    if test_workflow_repo:
        test_workflow_repo.log_stage(
            underwriting_id=underwriting_data.get('id'),
            workflow_name="Workflow 1",
            stage="prepare_processor",
            payload={
                "underwriting_processor_id": underwriting_processor_id,
                "processor_name": processor_name,
                "duplicate": duplicate
            },
            input={
                "processor_config": {
                    "processor": processor_config['processor'],
                    "enabled": processor_config.get('enabled'),
                    "auto": processor_config.get('auto'),
                    "current_executions_list": processor_config.get('current_executions_list', [])
                },
                "payload_list": payload_list
            },
            output={
                "execution_list": execution_list,
                "new_executions": new_exe_list,
                "deleted_executions": del_exe_list,
                "skipped_executions": skipped_exe_list,
                "result": "OK"
            },
            status="completed",
            execution_time_ms=step_time,
            metadata={
                "payloads_generated": len(payload_list),
                "executions_total": len(execution_list),
                "new_executions": len(new_exe_list),
                "deleted_executions": len(del_exe_list),
                "skipped_executions": len(skipped_exe_list)
            }
        )
    
    # Return only new executions
    return new_exe_list


def generate_execution(
    underwriting_processor_id: str,
    payload: dict[str, Any],
    processor_repo: ProcessorRepository,
    execution_repo: ExecutionRepository,
    test_workflow_repo: Optional[TestWorkflowRepository] = None,
    duplicate: bool = False
) -> str:
    """
    Generate execution: Create or reuse execution based on payload hash.
    
    Steps:
    1. Generate hash from payload
    2. Find existing execution with same hash
    3. If exists and not duplicate: return existing ID
    4. If exists and duplicate: create new with link
    5. If not exists: create new
    
    Args:
        underwriting_processor_id: The underwriting processor ID
        payload: Execution payload
        processor_repo: Repository for processor configuration
        execution_repo: Repository for execution management
        test_workflow_repo: Optional repository for test workflow tracking
        duplicate: Allow creating duplicate execution
        
    Returns:
        Execution ID (new or existing)
    """
    step_start = datetime.now()
    
    # Get processor config for underwriting_id (needed for logging)
    processor_config = processor_repo.get_underwriting_processor_by_id(
        underwriting_processor_id
    )
    
    # Generate hash from payload using utility function
    payload_hash = generate_payload_hash(payload)
    
    # Find existing execution with same hash
    existing = execution_repo.find_execution_by_hash(
        underwriting_processor_id=underwriting_processor_id,
        payload_hash=payload_hash
    )
    
    if existing and not duplicate:
        # Return existing execution ID
        return existing['id']
    
    # Create new execution
    execution_id = execution_repo.create_execution(
        underwriting_id=processor_config['underwriting_id'],
        underwriting_processor_id=underwriting_processor_id,
        organization_id=processor_config['organization_id'],
        processor_name=processor_config['processor'],
        payload=payload,
        payload_hash=payload_hash
    )
    
    # Log generate_execution with proper payload/input/output
    step_time = int((datetime.now() - step_start).total_seconds() * 1000)
    action_taken = "duplicated" if (existing and duplicate) else ("reused_existing" if existing else "created_new")
    
    if test_workflow_repo:
        test_workflow_repo.log_stage(
            underwriting_id=processor_config['underwriting_id'],
            workflow_name="Workflow 1",
            stage="generate_execution",
            payload={
                "underwriting_processor_id": underwriting_processor_id,
                "duplicate": duplicate
            },
            input={
                "payload": payload,
                "existing_execution": {
                    "found": existing is not None,
                    "execution_id": existing['id'] if existing else None
                } if existing else None
            },
            output={
                "execution_id": execution_id,
                "payload_hash": payload_hash,
                "action": action_taken,
                "updated_execution_id": existing['id'] if (existing and duplicate) else None
            },
            status="completed",
            execution_time_ms=step_time,
            metadata={
                "existing_found": existing is not None,
                "is_duplicate": duplicate,
                "processor": processor_config['processor']
            }
        )
    
    return execution_id
