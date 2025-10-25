"""
Consolidation Service

Plain function for factor consolidation across processor executions.
"""

from typing import Any

from ..repositories import (
    ProcessorRepository,
    ExecutionRepository,
    FactorRepository,
)
from .registry import get_registry
import psycopg2
from psycopg2.extras import RealDictCursor


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
    # Get database connection
    db_connection = psycopg2.connect(
        host="localhost",
        port=5432,
        database="aura_underwriting",
        user="aura_user",
        password="aura_password",
        cursor_factory=RealDictCursor,
    )

    # Instantiate repositories and set database connection
    processor_repo = ProcessorRepository()
    processor_repo.__init__(db_connection)

    execution_repo = ExecutionRepository()
    execution_repo.__init__(db_connection)

    factor_repo = FactorRepository()
    factor_repo.__init__(db_connection)

    results = []

    for underwriting_processor_id in processor_list:
        print(f"  Consolidating: {underwriting_processor_id}")

        try:
            processor_config = processor_repo.get_underwriting_processor_by_id(
                underwriting_processor_id
            )

            if not processor_config:
                print("    ⚠️  Processor config not found")
                continue

            active_executions = execution_repo.get_active_executions(
                underwriting_processor_id=underwriting_processor_id
            )

            # Handle None active_executions
            if active_executions is None:
                active_executions = []
                print("    ⚠️  No active executions found (None returned)")
            else:
                print(f"    Active executions: {len(active_executions)}")

            processor_registry = get_registry()
            if not processor_registry.is_processor_registered(
                processor_config["processor"]
            ):
                print(
                    f"    ⚠️  Processor not registered: {processor_config['processor']}"
                )
                continue

            processor_class = processor_registry.get_processor(
                processor_config["processor"]
            )

            # Extract factors from each execution's factors_delta
            factors_list: list[dict[str, Any]] = []
            for execution in active_executions:
                # Handle None execution
                if execution is None:
                    print("    ⚠️  Found None execution, skipping")
                    continue

                # Handle None factors_delta safely
                factors_delta = execution.get("factors_delta", {}) if execution else {}
                if factors_delta is None:
                    factors_delta = {}

                factors = factors_delta.get("factors", {}) if factors_delta else {}
                factors_list.append(factors)

            consolidated_factors = processor_class.consolidate(factors_list)

            print(f"    ✅ Consolidated: {consolidated_factors}")

            # Save factors to database
            if consolidated_factors:

                # Get the latest execution_id for lineage tracking
                latest_execution_id = None
                if active_executions and len(active_executions) > 0:
                    first_execution = active_executions[0]
                    if first_execution is not None:
                        latest_execution_id = first_execution.get("id")

                success = factor_repo.save_factors(
                    organization_id=processor_config.get("organization_id"),
                    underwriting_id=processor_config.get("underwriting_id"),
                    underwriting_processor_id=underwriting_processor_id,
                    execution_id=latest_execution_id,
                    factors=consolidated_factors,
                    source="processor",
                )

                if success:
                    print(
                        f"    💾 Saved {len(consolidated_factors)} factors to database"
                    )
                else:
                    print("    ❌ Failed to save factors to database")

            results.append(
                {
                    "success": True,
                    "underwriting_processor_id": underwriting_processor_id,
                    "processor": processor_config["processor"],
                    "factors": consolidated_factors,
                    "execution_count": len(active_executions),
                }
            )

            print(f"    Factors to save: {list(consolidated_factors.keys())}")

        except Exception as e:
            print(f"    ❌ Consolidation failed: {e}")

            results.append(
                {
                    "success": False,
                    "underwriting_processor_id": underwriting_processor_id,
                    "error": str(e),
                }
            )

    consolidated = sum(1 for r in results if r.get("success"))

    return {"consolidated": consolidated, "results": results}
