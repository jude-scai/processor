"""
Orchestration Service (Legacy Wrapper)

This module maintains backward compatibility by wrapping the new service-based architecture.
The actual implementation has been refactored into:
- services/orchestrator.py - Main coordination
- services/filtration.py - Processor selection and execution generation
- services/execution.py - Processor execution management
- services/consolidation.py - Factor consolidation
- utils/payload.py - Payload formatting
- utils/hashing.py - Hash generation

This wrapper delegates all calls to the new Orchestrator service.
"""

from typing import Any, Optional

from .services.orchestrator import Orchestrator, create_orchestrator as create_new_orchestrator
from .base_processor import BaseProcessor


class OrchestrationService:
    """
    Legacy orchestration service wrapper for backward compatibility.
    
    Delegates all operations to the new Orchestrator service.
    """
    
    def __init__(
        self,
        processor_repo: Any,
        execution_repo: Any,
        underwriting_repo: Any,
        test_workflow_repo: Optional[Any] = None
    ):
        """
        Initialize orchestration service with repositories.
        
        Args:
            processor_repo: Repository for processor configuration
            execution_repo: Repository for execution management
            underwriting_repo: Repository for underwriting data
            test_workflow_repo: Optional repository for test workflow tracking
        """
        # Create the new orchestrator internally
        self._orchestrator = Orchestrator(
            processor_repo=processor_repo,
            execution_repo=execution_repo,
            underwriting_repo=underwriting_repo,
            test_workflow_repo=test_workflow_repo
        )
        
        # Keep references for backward compatibility
        self.processor_repo = processor_repo
        self.execution_repo = execution_repo
        self.underwriting_repo = underwriting_repo
        self.test_workflow_repo = test_workflow_repo
        self._processor_registry = self._orchestrator._processor_registry
    
    def register_processor(self, processor_name: str, processor_class: type[BaseProcessor]):
        """
        Register a processor class for orchestration.
        
        Args:
            processor_name: Processor identifier (e.g., 'p_bank_statement')
            processor_class: Processor class to instantiate
        """
        self._orchestrator.register_processor(processor_name, processor_class)
    
    def handle_workflow1(self, underwriting_id: str) -> dict[str, Any]:
        """
        Handle Workflow 1: Automatic processor execution.
        
        Delegates to the new Orchestrator service.
        
        Args:
            underwriting_id: The underwriting ID to process
            
        Returns:
            Workflow execution results with counts and details
        """
        return self._orchestrator.handle_workflow1(underwriting_id)


# ============================================================================
# Helper function to create orchestration service (Legacy wrapper)
# ============================================================================

def create_orchestration_service(
    db_connection: Any,
    enable_test_tracking: bool = True
) -> OrchestrationService:
    """
    Create orchestration service with initialized repositories.
    
    This is a legacy wrapper that creates the new Orchestrator internally.
    
    Args:
        db_connection: Database connection
        enable_test_tracking: Enable test workflow tracking for debugging
        
    Returns:
        Configured OrchestrationService instance (wrapping new Orchestrator)
    """
    orchestrator = create_new_orchestrator(
        db_connection=db_connection,
        enable_test_tracking=enable_test_tracking
    )
    
    # Wrap in legacy OrchestrationService for backward compatibility
    # Note: We can't directly return orchestrator because the __init__ signature differs
    # So we construct using the repositories from the orchestrator
    return OrchestrationService(
        processor_repo=orchestrator.processor_repo,
        execution_repo=orchestrator.execution_repo,
        underwriting_repo=orchestrator.underwriting_repo,
        test_workflow_repo=orchestrator.test_workflow_repo
    )

