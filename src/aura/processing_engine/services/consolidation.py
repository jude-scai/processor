"""
Consolidation Service

Plain function for factor consolidation across processor executions.
"""

from datetime import datetime
from typing import Any, Optional

from ..repositories import (
    ProcessorRepository,
    ExecutionRepository,
    FactorRepository,
)
from .registry import get_registry


def consolidation(
    processor_list: list[str],
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

    Returns:
        Consolidation results with counts
    """
    # Instantiate repositories directly
    processor_repo = ProcessorRepository()
    execution_repo = ExecutionRepository()
    factor_repo = FactorRepository()
    
    # Initialize factor_repo with database connection from processor_repo
    if hasattr(processor_repo, 'db') and processor_repo.db is not None:
        factor_repo.__init__(processor_repo.db)

    results = []

    for underwriting_processor_id in processor_list:
        step_start = datetime.now()
        print(f"  Consolidating: {underwriting_processor_id}")

        try:
            processor_config = processor_repo.get_underwriting_processor_by_id(
                underwriting_processor_id
            )

            if not processor_config:
                print("    ⚠️  Processor config not found")
                continue

            processor_name = processor_config["processor"]

            active_executions = execution_repo.get_active_executions(
                underwriting_processor_id=underwriting_processor_id
            )

            print(f"    Active executions: {len(active_executions)}")

            processor_registry = get_registry()
            if not processor_registry.is_processor_registered(processor_name):
                print(f"    ⚠️  Processor not registered: {processor_name}")
                continue

            processor_class = processor_registry.get_processor(processor_name)

            # Extract factors from each execution's factors_delta
            factors_list = []
            for execution in active_executions:
                factors_delta = execution.get("factors_delta", {})
                factors = factors_delta.get("factors", {})
                factors_list.append(factors)

            consolidated_factors = processor_class.consolidate(factors_list)

            print(f"    ✅ Consolidated: {(consolidated_factors)}")

            # Save factors to database
            if consolidated_factors:
                # Get organization_id and underwriting_id from processor config
                organization_id = processor_config.get("organization_id")
                underwriting_id = processor_config.get("underwriting_id")
                
                # Get the latest execution_id for lineage tracking
                latest_execution_id = active_executions[0].get("id") if active_executions else None

                success = factor_repo.save_factors(
                    organization_id=organization_id,
                    underwriting_id=underwriting_id,
                    underwriting_processor_id=underwriting_processor_id,
                    execution_id=latest_execution_id,
                    factors=consolidated_factors,
                    source="processor"
                )

                if success:
                    print(f"    💾 Saved {len(consolidated_factors)} factors to database")
                else:
                    print(f"    ❌ Failed to save factors to database")

            step_time = int((datetime.now() - step_start).total_seconds() * 1000)

            results.append(
                {
                    "success": True,
                    "underwriting_processor_id": underwriting_processor_id,
                    "processor": processor_name,
                    "factors": consolidated_factors,
                    "execution_count": len(active_executions),
                }
            )

            print(f"    Factors to save: {list(consolidated_factors.keys())}")

        except Exception as e:
            print(f"    ❌ Consolidation failed: {e}")

            step_time = int((datetime.now() - step_start).total_seconds() * 1000)

            results.append(
                {
                    "success": False,
                    "underwriting_processor_id": underwriting_processor_id,
                    "error": str(e),
                }
            )

    consolidated = sum(1 for r in results if r.get("success"))

    return {"consolidated": consolidated, "results": results}
