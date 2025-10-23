"""
Test Workflow Repository

Handles database operations for test_workflow table.
Used for debugging and testing orchestration workflows.
"""

from typing import Any, Optional
import json
import hashlib
from datetime import datetime
from decimal import Decimal


def _json_serial(obj):
    """JSON serializer for objects not serializable by default."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, Decimal):
        return float(obj)
    return str(obj)  # Fallback for any other type


class TestWorkflowRepository:
    """
    Repository for test workflow tracking.
    
    Logs workflow execution stages for debugging and testing.
    """
    
    def __init__(self, db_connection: Any):
        """
        Initialize repository with database connection.
        
        Args:
            db_connection: Database connection
        """
        self.db = db_connection
    
    def log_stage(
        self,
        underwriting_id: str,
        workflow_name: str,
        stage: str,
        payload: dict[str, Any],
        input: Optional[dict[str, Any]] = None,
        output: Optional[dict[str, Any]] = None,
        status: str = 'completed',
        error_message: Optional[str] = None,
        execution_time_ms: Optional[int] = None,
        metadata: Optional[dict[str, Any]] = None
    ) -> str:
        """
        Log a workflow stage execution.
        
        Args:
            underwriting_id: The underwriting ID
            workflow_name: Workflow identifier (e.g., 'Workflow 1')
            stage: Stage name (e.g., 'filtration', 'execution', 'consolidation')
            payload: Input data for this stage
            output: Output/result of this stage
            status: Stage status ('started', 'completed', 'failed')
            error_message: Error details if failed
            execution_time_ms: Execution time in milliseconds
            metadata: Additional debug info
            
        Returns:
            Test workflow record ID
        """
        try:
            cursor = self.db.cursor()
            
            # Generate hash from payload
            payload_hash = self._generate_hash(payload)
            
            cursor.execute("""
                INSERT INTO test_workflow (
                    underwriting_id,
                    workflow_name,
                    stage,
                    payload,
                    input,
                    payload_hash,
                    output,
                    status,
                    error_message,
                    execution_time_ms,
                    metadata
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
                RETURNING id
            """, (
                underwriting_id,
                workflow_name,
                stage,
                json.dumps(payload, default=_json_serial),
                json.dumps(input, default=_json_serial) if input else None,
                payload_hash,
                json.dumps(output, default=_json_serial) if output else None,
                status,
                error_message,
                execution_time_ms,
                json.dumps(metadata, default=_json_serial) if metadata else None
            ))
            
            result = cursor.fetchone()
            test_workflow_id = result['id']
            
            self.db.commit()
            return str(test_workflow_id)
            
        except Exception as e:
            self.db.rollback()
            print(f"Error logging test workflow stage: {e}")
            raise
    
    def get_workflow_stages(
        self,
        underwriting_id: Optional[str] = None,
        workflow_name: Optional[str] = None
    ) -> list[dict[str, Any]]:
        """
        Get workflow stage logs.
        
        Args:
            underwriting_id: Filter by underwriting ID
            workflow_name: Filter by workflow name
            
        Returns:
            List of workflow stage records
        """
        try:
            cursor = self.db.cursor()
            
            query = """
                SELECT 
                    id,
                    underwriting_id,
                    workflow_name,
                    stage,
                    payload,
                    payload_hash,
                    output,
                    status,
                    error_message,
                    execution_time_ms,
                    metadata,
                    created_at,
                    updated_at
                FROM test_workflow
                WHERE 1=1
            """
            params = []
            
            if underwriting_id:
                query += " AND underwriting_id = %s"
                params.append(underwriting_id)
            
            if workflow_name:
                query += " AND workflow_name = %s"
                params.append(workflow_name)
            
            query += " ORDER BY created_at ASC"
            
            cursor.execute(query, tuple(params))
            results = cursor.fetchall()
            
            cursor.close()
            return [dict(row) for row in results]
            
        except Exception as e:
            print(f"Error getting workflow stages: {e}")
            return []
    
    def clear_test_data(self, underwriting_id: Optional[str] = None) -> int:
        """
        Clear test workflow data.
        
        Args:
            underwriting_id: If provided, only clear for this underwriting
            
        Returns:
            Number of records deleted
        """
        try:
            cursor = self.db.cursor()
            
            if underwriting_id:
                cursor.execute("""
                    DELETE FROM test_workflow
                    WHERE underwriting_id = %s
                """, (underwriting_id,))
            else:
                cursor.execute("DELETE FROM test_workflow")
            
            deleted_count = cursor.rowcount
            self.db.commit()
            cursor.close()
            
            return deleted_count
            
        except Exception as e:
            self.db.rollback()
            print(f"Error clearing test workflow data: {e}")
            return 0
    
    def _generate_hash(self, payload: dict[str, Any]) -> str:
        """Generate hash from payload for deduplication tracking."""
        payload_str = json.dumps(payload, sort_keys=True, default=_json_serial)
        return hashlib.sha256(payload_str.encode()).hexdigest()[:16]  # Short hash for readability

