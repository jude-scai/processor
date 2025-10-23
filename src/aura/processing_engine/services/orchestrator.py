"""
Orchestrator Service

Main orchestration service that coordinates processor execution workflows.
"""

from datetime import datetime
from typing import Any, Optional

from ..repositories import ProcessorRepository, ExecutionRepository, UnderwritingRepository, TestWorkflowRepository
from ..base_processor import BaseProcessor
from . import filtration as filtration_service
from . import execution as execution_service
from . import consolidation as consolidation_service


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
        test_workflow_repo: Optional[TestWorkflowRepository] = None
    ):
        """
        Initialize orchestrator with repositories.
        
        Args:
            processor_repo: Repository for processor configuration
            execution_repo: Repository for execution management
            underwriting_repo: Repository for underwriting data
            test_workflow_repo: Optional repository for test workflow tracking
        """
        self.processor_repo = processor_repo
        self.execution_repo = execution_repo
        self.underwriting_repo = underwriting_repo
        self.test_workflow_repo = test_workflow_repo
        self._processor_registry: dict[str, type[BaseProcessor]] = {}
    
    def register_processor(self, processor_name: str, processor_class: type[BaseProcessor]):
        """
        Register a processor class for orchestration.
        
        Args:
            processor_name: Processor identifier (e.g., 'p_bank_statement')
            processor_class: Processor class to instantiate
        """
        self._processor_registry[processor_name] = processor_class
    
    # =========================================================================
    # WORKFLOW 1: AUTOMATIC EXECUTION
    # =========================================================================
    
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
        print(f"WORKFLOW 1: Automatic Execution")
        print(f"Underwriting ID: {underwriting_id}")
        print(f"{'='*70}\n")
        
        workflow_start = datetime.now()
        
        # Step 1: Filtration
        print("Step 1: Filtration")
        print("-" * 70)
        filtration_start = datetime.now()
        filtration_result = filtration_service.filtration(
            underwriting_id=underwriting_id,
            processor_repo=self.processor_repo,
            execution_repo=self.execution_repo,
            underwriting_repo=self.underwriting_repo,
            processor_registry=self._processor_registry,
            test_workflow_repo=self.test_workflow_repo
        )
        filtration_time = int((datetime.now() - filtration_start).total_seconds() * 1000)
        
        # Log filtration stage
        if self.test_workflow_repo:
            # Get underwriting data for payload
            underwriting = self.underwriting_repo.get_underwriting_with_details(underwriting_id)
            eligible_procs = filtration_result.get('eligible_processors', [])
            
            # Build payload with actual underwriting data from database
            payload_data = {}
            if underwriting:
                # Application form data
                merchant = underwriting.get('merchant', {})
                application_form = {}
                for key, value in merchant.items():
                    if key not in ['id', 'created_at', 'updated_at', 'created_by', 'updated_by']:
                        application_form[f'merchant.{key}'] = value
                
                payload_data = {
                    "application_form": application_form,
                    "owners_list": underwriting.get('owners', []),
                    "documents_list": []  # TODO: Add when document integration is ready
                }
            
            self.test_workflow_repo.log_stage(
                underwriting_id=underwriting_id,
                workflow_name="Workflow 1",
                stage="filtration",
                payload=payload_data,
                input={
                    "eligible_processors": [
                        {
                            "underwriting_processor_id": p['id'],
                            "processor": p['processor'],
                            "enabled": p.get('enabled'),
                            "auto": p.get('auto'),
                            "current_executions_list": p.get('current_executions_list', [])
                        }
                        for p in eligible_procs
                    ]
                },
                output={
                    "processor_list": filtration_result['processor_list'],
                    "execution_list": filtration_result['execution_list']
                },
                status="completed",
                execution_time_ms=filtration_time,
                metadata={
                    "processors_found": len(eligible_procs),
                    "processors_selected": len(filtration_result['processor_list']),
                    "executions_to_run": len(filtration_result['execution_list'])
                }
            )
        
        processor_list = filtration_result['processor_list']
        execution_list = filtration_result['execution_list']
        
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
                    "consolidation_results": []
                }
            }
        
        # Step 2: Execution
        print("Step 2: Execution")
        print("-" * 70)
        execution_start = datetime.now()
        execution_result = execution_service.execution(
            execution_list=execution_list,
            processor_repo=self.processor_repo,
            execution_repo=self.execution_repo,
            processor_registry=self._processor_registry,
            test_workflow_repo=self.test_workflow_repo
        )
        execution_time = int((datetime.now() - execution_start).total_seconds() * 1000)
        
        # Log execution stage
        if self.test_workflow_repo:
            self.test_workflow_repo.log_stage(
                underwriting_id=underwriting_id,
                workflow_name="Workflow 1",
                stage="execution",
                payload={"execution_list": execution_list},
                output=execution_result,
                status="completed",
                execution_time_ms=execution_time,
                metadata={
                    "total_executions": len(execution_list),
                    "completed": execution_result['completed'],
                    "failed": execution_result['failed']
                }
            )
        
        print(f"  Executions completed: {execution_result['completed']}")
        print(f"  Executions failed: {execution_result['failed']}")
        print()
        
        # Step 3: Consolidation
        print("Step 3: Consolidation")
        print("-" * 70)
        consolidation_start = datetime.now()
        consolidation_result = consolidation_service.consolidation(
            processor_list=processor_list,
            processor_repo=self.processor_repo,
            execution_repo=self.execution_repo,
            processor_registry=self._processor_registry,
            test_workflow_repo=self.test_workflow_repo
        )
        consolidation_time = int((datetime.now() - consolidation_start).total_seconds() * 1000)
        
        # Log consolidation stage
        if self.test_workflow_repo:
            self.test_workflow_repo.log_stage(
                underwriting_id=underwriting_id,
                workflow_name="Workflow 1",
                stage="consolidation",
                payload={"processor_list": processor_list},
                output=consolidation_result,
                status="completed",
                execution_time_ms=consolidation_time,
                metadata={
                    "processors_to_consolidate": len(processor_list),
                    "consolidated": consolidation_result['consolidated']
                }
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
            "executions_run": execution_result['completed'],
            "executions_failed": execution_result['failed'],
            "processors_consolidated": consolidation_result['consolidated'],
            "details": {
                "processor_list": processor_list,
                "execution_results": execution_result['results'],
                "consolidation_results": consolidation_result['results']
            }
        }


# ============================================================================
# Helper function to create orchestrator
# ============================================================================

def create_orchestrator(
    db_connection: Any,
    enable_test_tracking: bool = True
) -> Orchestrator:
    """
    Create orchestrator with initialized repositories.
    
    Args:
        db_connection: Database connection
        enable_test_tracking: Enable test workflow tracking for debugging
        
    Returns:
        Configured Orchestrator instance
    """
    processor_repo = ProcessorRepository(db_connection)
    execution_repo = ExecutionRepository(db_connection)
    underwriting_repo = UnderwritingRepository(db_connection)
    test_workflow_repo = TestWorkflowRepository(db_connection) if enable_test_tracking else None
    
    return Orchestrator(
        processor_repo=processor_repo,
        execution_repo=execution_repo,
        underwriting_repo=underwriting_repo,
        test_workflow_repo=test_workflow_repo
    )

