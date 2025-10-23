"""
Consolidation Service

Plain function for factor consolidation across processor executions.
"""

from datetime import datetime
from typing import Any, Optional

from ..repositories import ProcessorRepository, ExecutionRepository, TestWorkflowRepository
from ..base_processor import BaseProcessor


def consolidation(
    processor_list: list[str],
    processor_repo: ProcessorRepository,
    execution_repo: ExecutionRepository,
    processor_registry: dict[str, type[BaseProcessor]],
    test_workflow_repo: Optional[TestWorkflowRepository] = None
) -> dict[str, Any]:
    """
    Consolidate execution results for multiple processors.
    
    Steps:
    1. For each processor in list
    2. Get active executions for processor
    3. Run processor's consolidate method
    4. Update factors in database
    
    Args:
        processor_list: List of underwriting_processor_ids to consolidate
        processor_repo: Repository for processor configuration
        execution_repo: Repository for execution management
        processor_registry: Registry of processor classes
        test_workflow_repo: Optional repository for test workflow tracking
        
    Returns:
        Consolidation results with counts
    """
    results = []
    
    for underwriting_processor_id in processor_list:
        step_start = datetime.now()
        print(f"  Consolidating: {underwriting_processor_id}")
        
        try:
            # Get processor config
            processor_config = processor_repo.get_underwriting_processor_by_id(
                underwriting_processor_id
            )
            
            if not processor_config:
                print(f"    ⚠️  Processor config not found")
                continue
            
            processor_name = processor_config['processor']
            
            # Get active executions
            active_executions = execution_repo.get_active_executions(
                underwriting_processor_id=underwriting_processor_id
            )
            
            print(f"    Active executions: {len(active_executions)}")
            
            # Get processor class
            if processor_name not in processor_registry:
                print(f"    ⚠️  Processor not registered: {processor_name}")
                continue
            
            processor_class = processor_registry[processor_name]
            
            # Run consolidate (static method)
            consolidated_factors = processor_class.consolidate(active_executions)
            
            print(f"    ✅ Consolidated: {len(consolidated_factors)} factors")
            
            # Log consolidate_processor step
            step_time = int((datetime.now() - step_start).total_seconds() * 1000)
            if test_workflow_repo:
                test_workflow_repo.log_stage(
                    underwriting_id=processor_config['underwriting_id'],
                    workflow_name="Workflow 1",
                    stage="consolidate_processor",
                    payload={
                        "underwriting_processor_id": underwriting_processor_id,
                        "processor": processor_name
                    },
                    input={
                        "active_executions": [
                            {
                                "execution_id": ex.get('id'),
                                "status": ex.get('status'),
                                "factors_delta_keys": list(ex.get('factors_delta', {}).keys()) if ex.get('factors_delta') else []
                            }
                            for ex in active_executions
                        ]
                    },
                    output={
                        "result": "success",
                        "factors": consolidated_factors,
                        "factor_count": len(consolidated_factors)
                    },
                    status="completed",
                    execution_time_ms=step_time,
                    metadata={
                        "processor": processor_name,
                        "executions_used": len(active_executions),
                        "execution_ids": [ex['id'] for ex in active_executions]
                    }
                )
            
            results.append({
                "success": True,
                "underwriting_processor_id": underwriting_processor_id,
                "processor": processor_name,
                "factors": consolidated_factors,
                "execution_count": len(active_executions)
            })
            
            # TODO: Save factors to database via factor repository
            # For now, just log what would be saved
            print(f"    Factors to save: {list(consolidated_factors.keys())}")
            
        except Exception as e:
            print(f"    ❌ Consolidation failed: {e}")
            
            # Log consolidation error
            step_time = int((datetime.now() - step_start).total_seconds() * 1000)
            if test_workflow_repo and processor_config:
                test_workflow_repo.log_stage(
                    underwriting_id=processor_config.get('underwriting_id'),
                    workflow_name="Workflow 1",
                    stage="consolidate_processor",
                    payload={
                        "underwriting_processor_id": underwriting_processor_id,
                        "processor": processor_config.get('processor', 'unknown')
                    },
                    input=None,
                    output={
                        "result": "error",
                        "error": str(e)
                    },
                    status="failed",
                    execution_time_ms=step_time,
                    error_message=str(e),
                    metadata={
                        "exception_type": type(e).__name__
                    }
                )
            
            results.append({
                "success": False,
                "underwriting_processor_id": underwriting_processor_id,
                "error": str(e)
            })
    
    consolidated = sum(1 for r in results if r.get('success'))
    
    return {
        "consolidated": consolidated,
        "results": results
    }
