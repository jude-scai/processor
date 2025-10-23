"""
Orchestration Service

Implements the processor orchestration workflows based on Pub/Sub events.
Currently implements Workflow 1 (Automatic Execution).

Workflow 1: underwriting.updated / document.analyzed
- Filtration: Determine which processors should run
- Execution: Run pending processor executions in parallel
- Consolidation: Aggregate results and calculate factors
"""

from typing import Any, Optional
import concurrent.futures
from datetime import datetime
import json

from .repositories import ProcessorRepository, ExecutionRepository, UnderwritingRepository, TestWorkflowRepository
from .base_processor import BaseProcessor


class OrchestrationService:
    """
    Orchestration service for processor execution workflows.
    
    Handles the complete lifecycle of processor execution from event reception
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
        Initialize orchestration service with repositories.
        
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
        self._processor_registry = {}  # Will store processor instances
    
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
        filtration_result = self._filtration(underwriting_id)
        filtration_time = int((datetime.now() - filtration_start).total_seconds() * 1000)
        
        # Log filtration stage
        if self.test_workflow_repo:
            self.test_workflow_repo.log_stage(
                underwriting_id=underwriting_id,
                workflow_name="Workflow 1",
                stage="filtration",
                payload={"underwriting_id": underwriting_id},
                output=filtration_result,
                status="completed",
                execution_time_ms=filtration_time,
                metadata={
                    "processors_found": len(filtration_result['processor_list']),
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
        execution_result = self._execution(execution_list)
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
        consolidation_result = self._consolidation(processor_list)
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
    
    # =========================================================================
    # FILTRATION
    # =========================================================================
    
    def _filtration(self, underwriting_id: str) -> dict[str, Any]:
        """
        Filtration step: Determine which processors should run.
        
        Steps:
        1. Get underwriting data
        2. Get processors (enabled=true, auto=true)
        3. For each processor, call prepare_processor
        4. Build processor_list and execution_list
        
        Args:
            underwriting_id: The underwriting ID
            
        Returns:
            Dictionary with processor_list and execution_list
        """
        # Step 1: Get underwriting data
        underwriting = self.underwriting_repo.get_underwriting_with_details(underwriting_id)
        
        if not underwriting:
            print(f"  ⚠️  Underwriting not found: {underwriting_id}")
            return {"processor_list": [], "execution_list": []}
        
        # Step 2: Get processors (enabled=true, auto=true)
        processors = self.processor_repo.get_underwriting_processors(
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
            prepare_result = self._prepare_processor(
                underwriting_processor_id=underwriting_processor_id,
                underwriting_data=underwriting
            )
            
            # Check result
            if prepare_result is None:
                print(f"    ℹ️  No triggers matched - skipped")
            elif isinstance(prepare_result, list):
                if len(prepare_result) == 0:
                    print(f"    ✅ Triggers matched, no new executions needed")
                else:
                    print(f"    ✅ Triggers matched, {len(prepare_result)} new execution(s)")
                
                # Add to processor_list (for consolidation)
                processor_list.append(underwriting_processor_id)
                
                # Add to execution_list (for execution)
                execution_list.extend(prepare_result)
        
        return {
            "processor_list": processor_list,
            "execution_list": execution_list
        }
    
    def _prepare_processor(
        self,
        underwriting_processor_id: str,
        underwriting_data: dict[str, Any],
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
            duplicate: Allow duplicate executions
            
        Returns:
            List of execution IDs to run, empty list if triggers matched but no new executions,
            or None if no triggers matched
        """
        step_start = datetime.now()
        
        # Get processor configuration
        processor_config = self.processor_repo.get_underwriting_processor_by_id(
            underwriting_processor_id
        )
        
        if not processor_config:
            return None
        
        processor_name = processor_config['processor']
        
        # Get processor instance from registry
        if processor_name not in self._processor_registry:
            print(f"      ⚠️  Processor not registered: {processor_name}")
            return None
        
        processor_class = self._processor_registry[processor_name]
        processor = processor_class(processor_repo=self.processor_repo)
        processor._underwriting_processor_id = underwriting_processor_id
        
        # Format payload list (implemented in BaseProcessor)
        payload_list = processor.format_payload_list(underwriting_data)
        
        if not payload_list:
            # No triggers matched or no data available
            return None
        
        # Generate executions for each payload
        execution_list = []
        for payload in payload_list:
            execution_id = self._generate_execution(
                underwriting_processor_id=underwriting_processor_id,
                payload=payload,
                duplicate=duplicate
            )
            execution_list.append(execution_id)
        
        # Get current executions for this processor
        current_executions = processor_config.get('current_executions_list', [])
        
        # Calculate new and deleted executions
        new_exe_list = [eid for eid in execution_list if eid not in current_executions]
        del_exe_list = [eid for eid in current_executions if eid not in execution_list]
        
        # If both lists empty, no changes
        if not new_exe_list and not del_exe_list:
            return None
        
        # Update current executions
        self.processor_repo.update_current_executions_list(
            underwriting_processor_id=underwriting_processor_id,
            execution_ids=execution_list
        )
        
        # Log prepare_processor step
        step_time = int((datetime.now() - step_start).total_seconds() * 1000)
        if self.test_workflow_repo:
            self.test_workflow_repo.log_stage(
                underwriting_id=underwriting_data.get('id'),
                workflow_name="Workflow 1",
                stage="prepare_processor",
                payload={
                    "underwriting_processor_id": underwriting_processor_id,
                    "processor_name": processor_name,
                    "duplicate": duplicate
                },
                output={
                    "payload_list": payload_list,
                    "execution_list": execution_list,
                    "new_executions": new_exe_list,
                    "deleted_executions": del_exe_list,
                    "result": "NULL" if (not new_exe_list and not del_exe_list) else "OK"
                },
                status="completed",
                execution_time_ms=step_time,
                metadata={
                    "payloads_generated": len(payload_list),
                    "executions_created": len(execution_list),
                    "new_executions": len(new_exe_list),
                    "deleted_executions": len(del_exe_list)
                }
            )
        
        # Return only new executions
        return new_exe_list
    
    def _generate_execution(
        self,
        underwriting_processor_id: str,
        payload: dict[str, Any],
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
            duplicate: Allow creating duplicate execution
            
        Returns:
            Execution ID (new or existing)
        """
        step_start = datetime.now()
        
        # Generate hash from payload
        import hashlib
        
        # Custom JSON encoder to handle datetime and Decimal objects
        from decimal import Decimal
        def json_serial(obj):
            """JSON serializer for objects not serializable by default json code"""
            if isinstance(obj, datetime):
                return obj.isoformat()
            if isinstance(obj, Decimal):
                return float(obj)
            raise TypeError(f"Type {type(obj)} not serializable")
        
        payload_str = json.dumps(payload, sort_keys=True, default=json_serial)
        payload_hash = hashlib.sha256(payload_str.encode()).hexdigest()
        
        # Find existing execution with same hash
        existing = self.execution_repo.find_execution_by_hash(
            underwriting_processor_id=underwriting_processor_id,
            payload_hash=payload_hash
        )
        
        if existing and not duplicate:
            # Return existing execution ID
            return existing['id']
        
        # Get processor config for organization_id and underwriting_id
        processor_config = self.processor_repo.get_underwriting_processor_by_id(
            underwriting_processor_id
        )
        
        # Create new execution
        execution_id = self.execution_repo.create_execution(
            underwriting_id=processor_config['underwriting_id'],
            underwriting_processor_id=underwriting_processor_id,
            organization_id=processor_config['organization_id'],
            processor_name=processor_config['processor'],
            payload=payload,
            payload_hash=payload_hash
        )
        
        # Log generate_execution step
        step_time = int((datetime.now() - step_start).total_seconds() * 1000)
        action_taken = "reused_existing" if (existing and not duplicate) else ("duplicated" if duplicate else "created_new")
        
        if self.test_workflow_repo:
            self.test_workflow_repo.log_stage(
                underwriting_id=processor_config['underwriting_id'],
                workflow_name="Workflow 1",
                stage="generate_execution",
                payload={
                    "underwriting_processor_id": underwriting_processor_id,
                    "payload": payload,
                    "duplicate": duplicate
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
    
    # =========================================================================
    # EXECUTION
    # =========================================================================
    
    def _execution(self, execution_list: list[str]) -> dict[str, Any]:
        """
        Execution step: Run pending processor executions in parallel.
        
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
        
        results = []
        
        # Use ThreadPoolExecutor for parallel execution
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = []
            
            for execution_id in execution_list:
                # Get execution data
                execution = self.execution_repo.get_execution_by_id(execution_id)
                
                if not execution:
                    print(f"    ⚠️  Execution not found: {execution_id}")
                    continue
                
                # Only execute if status is pending
                if execution['status'] == 'pending':
                    print(f"    Launching execution: {execution_id}")
                    future = executor.submit(self._run_execution, execution)
                    futures.append(future)
                else:
                    print(f"    ℹ️  Execution {execution_id} status: {execution['status']} - skipped")
            
            # Wait for all executions to complete
            for future in concurrent.futures.as_completed(futures):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    print(f"    ❌ Execution error: {e}")
                    results.append({"success": False, "error": str(e)})
        
        # Count results
        completed = sum(1 for r in results if r.get('success'))
        failed = sum(1 for r in results if not r.get('success'))
        
        return {
            "completed": completed,
            "failed": failed,
            "results": results
        }
    
    def _run_execution(self, execution: dict[str, Any]) -> dict[str, Any]:
        """
        Run a single processor execution.
        
        Args:
            execution: Execution record with processor, payload, etc.
            
        Returns:
            Execution result
        """
        step_start = datetime.now()
        execution_id = execution['id']
        processor_name = execution['processor']
        underwriting_processor_id = execution['underwriting_processor_id']
        underwriting_id = execution['underwriting_id']
        
        print(f"      Running: {execution_id} ({processor_name})")
        
        try:
            # Update status to running
            self.execution_repo.update_execution_status(
                execution_id=execution_id,
                status='running',
                started_at=datetime.now()
            )
            
            # Get processor instance
            if processor_name not in self._processor_registry:
                raise Exception(f"Processor not registered: {processor_name}")
            
            processor_class = self._processor_registry[processor_name]
            processor = processor_class(processor_repo=self.processor_repo)
            processor._underwriting_processor_id = underwriting_processor_id
            
            # Execute processor
            from .models import ExecutionPayload
            
            payload_data = execution['payload']
            exec_payload = ExecutionPayload(
                underwriting_id=execution['underwriting_id'],
                underwriting_processor_id=underwriting_processor_id,
                application_form=payload_data.get('application_form', {}),
                owners_list=payload_data.get('owners_list', []),
                documents_list=payload_data.get('documents_list', [])
            )
            
            result = processor.execute(
                execution_id=execution_id,
                underwriting_processor_id=underwriting_processor_id,
                payload=exec_payload
            )
            
            # Save execution result
            if result.is_successful():
                self.execution_repo.save_execution_result(
                    execution_id=execution_id,
                    output=result.output,
                    factors={},  # Factors calculated in consolidation
                    cost_cents=int(result.total_cost_cents),
                    completed_at=datetime.now()
                )
                
                print(f"      ✅ Completed: {execution_id}")
                
                # Log successful execution
                step_time = int((datetime.now() - step_start).total_seconds() * 1000)
                if self.test_workflow_repo:
                    self.test_workflow_repo.log_stage(
                        underwriting_id=underwriting_id,
                        workflow_name="Workflow 1",
                        stage="run_execution",
                        payload={
                            "execution_id": execution_id,
                            "processor": processor_name,
                            "underwriting_processor_id": underwriting_processor_id,
                            "input_payload": execution['payload']
                        },
                        output={
                            "result": "success",
                            "output": result.output,
                            "cost_cents": int(result.total_cost_cents)
                        },
                        status="completed",
                        execution_time_ms=step_time,
                        metadata={
                            "processor": processor_name,
                            "payload_hash": execution.get('payload_hash')
                        }
                    )
                
                return {
                    "success": True,
                    "execution_id": execution_id,
                    "processor": processor_name,
                    "output": result.output
                }
            else:
                # Update status to failed
                self.execution_repo.update_execution_status(
                    execution_id=execution_id,
                    status='failed',
                    completed_at=datetime.now(),
                    failed_reason=result.error_message
                )
                
                print(f"      ❌ Failed: {execution_id} - {result.error_message}")
                
                # Log failed execution
                step_time = int((datetime.now() - step_start).total_seconds() * 1000)
                if self.test_workflow_repo:
                    self.test_workflow_repo.log_stage(
                        underwriting_id=underwriting_id,
                        workflow_name="Workflow 1",
                        stage="run_execution",
                        payload={
                            "execution_id": execution_id,
                            "processor": processor_name,
                            "underwriting_processor_id": underwriting_processor_id,
                            "input_payload": execution['payload']
                        },
                        output={
                            "result": "failed",
                            "error": result.error_message
                        },
                        status="failed",
                        execution_time_ms=step_time,
                        error_message=result.error_message,
                        metadata={
                            "processor": processor_name,
                            "payload_hash": execution.get('payload_hash')
                        }
                    )
                
                return {
                    "success": False,
                    "execution_id": execution_id,
                    "processor": processor_name,
                    "error": result.error_message
                }
                
        except Exception as e:
            # Update status to failed
            self.execution_repo.update_execution_status(
                execution_id=execution_id,
                status='failed',
                completed_at=datetime.now(),
                failed_reason=str(e)
            )
            
            print(f"      ❌ Exception: {execution_id} - {e}")
            
            # Log exception
            step_time = int((datetime.now() - step_start).total_seconds() * 1000)
            if self.test_workflow_repo:
                self.test_workflow_repo.log_stage(
                    underwriting_id=underwriting_id,
                    workflow_name="Workflow 1",
                    stage="run_execution",
                    payload={
                        "execution_id": execution_id,
                        "processor": processor_name,
                        "underwriting_processor_id": underwriting_processor_id,
                        "input_payload": execution['payload']
                    },
                    output={
                        "result": "exception",
                        "error": str(e)
                    },
                    status="failed",
                    execution_time_ms=step_time,
                    error_message=str(e),
                    metadata={
                        "processor": processor_name,
                        "exception_type": type(e).__name__,
                        "payload_hash": execution.get('payload_hash')
                    }
                )
            
            return {
                "success": False,
                "execution_id": execution_id,
                "processor": processor_name,
                "error": str(e)
            }
    
    # =========================================================================
    # CONSOLIDATION
    # =========================================================================
    
    def _consolidation(self, processor_list: list[str]) -> dict[str, Any]:
        """
        Consolidation step: Aggregate execution results per processor.
        
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
        results = []
        
        for underwriting_processor_id in processor_list:
            step_start = datetime.now()
            print(f"  Consolidating: {underwriting_processor_id}")
            
            try:
                # Get processor config
                processor_config = self.processor_repo.get_underwriting_processor_by_id(
                    underwriting_processor_id
                )
                
                if not processor_config:
                    print(f"    ⚠️  Processor config not found")
                    continue
                
                processor_name = processor_config['processor']
                
                # Get active executions
                active_executions = self.execution_repo.get_active_executions(
                    underwriting_processor_id=underwriting_processor_id
                )
                
                print(f"    Active executions: {len(active_executions)}")
                
                # Get processor instance
                if processor_name not in self._processor_registry:
                    print(f"    ⚠️  Processor not registered: {processor_name}")
                    continue
                
                processor_class = self._processor_registry[processor_name]
                
                # Run consolidate (static method)
                consolidated_factors = processor_class.consolidate(active_executions)
                
                print(f"    ✅ Consolidated: {len(consolidated_factors)} factors")
                
                # Log consolidate_processor step
                step_time = int((datetime.now() - step_start).total_seconds() * 1000)
                if self.test_workflow_repo:
                    self.test_workflow_repo.log_stage(
                        underwriting_id=processor_config['underwriting_id'],
                        workflow_name="Workflow 1",
                        stage="consolidate_processor",
                        payload={
                            "underwriting_processor_id": underwriting_processor_id,
                            "processor": processor_name,
                            "active_execution_count": len(active_executions)
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
                if self.test_workflow_repo and processor_config:
                    self.test_workflow_repo.log_stage(
                        underwriting_id=processor_config.get('underwriting_id'),
                        workflow_name="Workflow 1",
                        stage="consolidate_processor",
                        payload={
                            "underwriting_processor_id": underwriting_processor_id,
                            "processor": processor_config.get('processor', 'unknown')
                        },
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


# ============================================================================
# Helper function to create orchestration service
# ============================================================================

def create_orchestration_service(
    db_connection: Any,
    enable_test_tracking: bool = True
) -> OrchestrationService:
    """
    Create orchestration service with initialized repositories.
    
    Args:
        db_connection: Database connection
        enable_test_tracking: Enable test workflow tracking for debugging
        
    Returns:
        Configured OrchestrationService instance
    """
    processor_repo = ProcessorRepository(db_connection)
    execution_repo = ExecutionRepository(db_connection)
    underwriting_repo = UnderwritingRepository(db_connection)
    test_workflow_repo = TestWorkflowRepository(db_connection) if enable_test_tracking else None
    
    return OrchestrationService(
        processor_repo=processor_repo,
        execution_repo=execution_repo,
        underwriting_repo=underwriting_repo,
        test_workflow_repo=test_workflow_repo
    )

