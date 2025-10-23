"""
Execution Repository

Handles database operations for processor executions:
- Create and manage execution records
- Track execution status and results
- Handle supersession relationships
- Store execution outputs
"""

from typing import Any, Optional
from datetime import datetime
from decimal import Decimal
import json


def _json_serial(obj):
    """JSON serializer for objects not serializable by default."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError(f"Type {type(obj)} not serializable")


class ExecutionRepository:
    """
    Repository for processor execution database operations.

    Manages:
    - Execution record creation and updates
    - Status tracking (pending, running, completed, failed)
    - Supersession relationships (updated_execution_id)
    - Execution outputs and metadata
    """

    def __init__(self, db_connection: Any):
        """
        Initialize the repository with a database connection.

        Args:
            db_connection: Database connection or session (PostgreSQL/BigQuery)
        """
        self.db = db_connection

    # =========================================================================
    # EXECUTION CREATION
    # =========================================================================

    def create_execution(
        self,
        underwriting_id: str,
        underwriting_processor_id: str,
        organization_id: str,
        processor_name: str,
        payload: dict[str, Any],
        payload_hash: str,
        document_revision_ids: Optional[list[str]] = None,
        document_ids_hash: Optional[str] = None
    ) -> str:
        """
        Create a new processor execution record.

        Args:
            underwriting_id: Underwriting UUID
            underwriting_processor_id: Underwriting processor UUID
            organization_id: Organization UUID
            processor_name: Processor identifier
            payload: Execution input payload
            payload_hash: Hash of the payload for deduplication
            document_revision_ids: List of document revision IDs used
            document_ids_hash: Hash of document IDs for tracking

        Returns:
            Execution ID (UUID)
        """
        execution_id = self._generate_uuid()

        query = """
        INSERT INTO processor_executions (
            id,
            organization_id,
            underwriting_id,
            underwriting_processor_id,
            processor,
            status,
            enabled,
            payload,
            payload_hash,
            created_at,
            updated_at
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        )
        """

        now = datetime.utcnow()

        try:
            cursor = self.db.cursor()
            cursor.execute(query, (
                execution_id,
                organization_id,
                underwriting_id,
                underwriting_processor_id,
                processor_name,
                'pending',
                True,
                json.dumps(payload, default=_json_serial),
                payload_hash,
                now,
                now
            ))
            self.db.commit()
            cursor.close()
        except Exception as e:
            print(f"Error creating execution: {e}")
            self.db.rollback()
            raise

        return execution_id

    def find_execution_by_hash(
        self,
        underwriting_processor_id: str,
        payload_hash: str
    ) -> Optional[dict[str, Any]]:
        """
        Find an existing execution by payload hash.

        Used for deduplication to avoid running identical executions.

        Args:
            underwriting_processor_id: Underwriting processor UUID
            payload_hash: Hash of the payload

        Returns:
            Execution record or None if not found
        """
        query = """
        SELECT
            id,
            underwriting_id,
            underwriting_processor_id,
            processor,
            status,
            enabled,
            payload,
            payload_hash,
            factors_delta,
            run_cost_cents,
            started_at,
            completed_at,
            failed_code,
            failed_reason,
            updated_execution_id,
            created_at
        FROM processor_executions
        WHERE underwriting_processor_id = %s
          AND payload_hash = %s
        ORDER BY created_at DESC
        LIMIT 1
        """
        try:
            cursor = self.db.cursor()
            cursor.execute(query, (underwriting_processor_id, payload_hash))
            result = cursor.fetchone()
            cursor.close()
            return dict(result) if result else None
        except Exception as e:
            print(f"Error finding execution by hash: {e}")
            return None

    # =========================================================================
    # EXECUTION STATUS UPDATES
    # =========================================================================

    def update_execution_status(
        self,
        execution_id: str,
        status: str,
        started_at: Optional[datetime] = None,
        completed_at: Optional[datetime] = None,
        failed_code: Optional[str] = None,
        failed_reason: Optional[str] = None
    ) -> bool:
        """
        Update the status of an execution.

        Args:
            execution_id: Execution UUID
            status: New status (pending, running, completed, failed)
            started_at: When execution started (for 'running' status)
            completed_at: When execution completed (for 'completed' status)
            failed_code: Error code (for 'failed' status)
            failed_reason: Error message (for 'failed' status)

        Returns:
            True if update successful
        """
        fields = ["status = %s", "updated_at = %s"]
        params = [status, datetime.utcnow()]

        if started_at:
            fields.append("started_at = %s")
            params.append(started_at)

        if completed_at:
            fields.append("completed_at = %s")
            params.append(completed_at)

        if failed_code:
            fields.append("failed_code = %s")
            params.append(failed_code)

        if failed_reason:
            fields.append("failed_reason = %s")
            params.append(failed_reason)

        params.append(execution_id)

        query = f"""
        UPDATE processor_executions
        SET {', '.join(fields)}
        WHERE id = %s
        """

        try:
            cursor = self.db.cursor()
            cursor.execute(query, params)
            self.db.commit()
            cursor.close()
            return True
        except Exception as e:
            print(f"Error updating execution status: {e}")
            self.db.rollback()
            return False

    def save_execution_result(
        self,
        execution_id: str,
        output: dict[str, Any],
        factors: Optional[dict[str, Any]],
        cost_cents: int,
        completed_at: datetime
    ) -> bool:
        """
        Save the execution result (output, factors, cost).

        Args:
            execution_id: Execution UUID
            output: Processor execution output (stored in factors_delta for now)
            factors: Additional factors (merged with output)
            cost_cents: Cost in cents
            completed_at: Completion timestamp

        Returns:
            True if save successful
        """
        # Merge output and factors (output takes precedence)
        # Store in factors_delta column since there's no output column
        combined_factors = {**(factors or {}), **output}
        
        query = """
        UPDATE processor_executions
        SET
            status = 'completed',
            factors_delta = %s,
            run_cost_cents = %s,
            completed_at = %s,
            updated_at = %s
        WHERE id = %s
        """

        now = datetime.utcnow()

        try:
            cursor = self.db.cursor()
            cursor.execute(query, (
                json.dumps(combined_factors, default=_json_serial) if combined_factors else None,
                cost_cents,
                completed_at,
                now,
                execution_id
            ))
            self.db.commit()
            cursor.close()
            return True
        except Exception as e:
            print(f"Error saving execution result: {e}")
            self.db.rollback()
            return False

    # =========================================================================
    # EXECUTION RETRIEVAL
    # =========================================================================

    def get_execution_by_id(
        self,
        execution_id: str
    ) -> Optional[dict[str, Any]]:
        """
        Get execution record by ID.

        Args:
            execution_id: Execution UUID

        Returns:
            Execution record or None
        """
        query = """
        SELECT
            id,
            organization_id,
            underwriting_id,
            underwriting_processor_id,
            processor,
            status,
            enabled,
            payload,
            payload_hash,
            factors_delta,
            run_cost_cents,
            started_at,
            completed_at,
            failed_code,
            failed_reason,
            updated_execution_id,
            created_at,
            updated_at
        FROM processor_executions
        WHERE id = %s
        """
        try:
            cursor = self.db.cursor()
            cursor.execute(query, (execution_id,))
            result = cursor.fetchone()
            cursor.close()
            return dict(result) if result else None
        except Exception as e:
            print(f"Error fetching execution by id: {e}")
            return None

    def get_active_executions(
        self,
        underwriting_processor_id: str
    ) -> list[dict[str, Any]]:
        """
        Get all active (current) executions for a processor.

        Active executions are those that:
        - Have enabled = true
        - Are in the current_executions_list of the underwriting processor
        - Have status = 'completed'

        Args:
            underwriting_processor_id: Underwriting processor UUID

        Returns:
            List of active execution records
        """
        query = """
        SELECT
            pe.id,
            pe.organization_id,
            pe.underwriting_id,
            pe.underwriting_processor_id,
            pe.processor,
            pe.status,
            pe.enabled,
            pe.payload,
            pe.payload_hash,
            pe.factors_delta,
            pe.run_cost_cents,
            pe.completed_at,
            pe.created_at
        FROM processor_executions pe
        INNER JOIN underwriting_processors up
            ON pe.underwriting_processor_id = up.id
        WHERE pe.underwriting_processor_id = %s
          AND pe.enabled = true
          AND pe.status = 'completed'
          AND pe.id = ANY(up.current_executions_list)
        ORDER BY pe.completed_at DESC
        """
        try:
            cursor = self.db.cursor()
            cursor.execute(query, (underwriting_processor_id,))
            results = cursor.fetchall()
            cursor.close()
            return [dict(row) for row in results] if results else []
        except Exception as e:
            print(f"Error fetching active executions: {e}")
            return []

    def get_executions_by_underwriting(
        self,
        underwriting_id: str,
        processor_name: Optional[str] = None,
        status: Optional[str] = None
    ) -> list[dict[str, Any]]:
        """
        Get all executions for an underwriting.

        Args:
            underwriting_id: Underwriting UUID
            processor_name: Optional filter by processor
            status: Optional filter by status

        Returns:
            List of execution records
        """
        query = """
        SELECT
            id,
            organization_id,
            underwriting_id,
            underwriting_processor_id,
            processor,
            status,
            enabled,
            factors_delta,
            run_cost_cents,
            started_at,
            completed_at,
            failed_code,
            failed_reason,
            created_at
        FROM processor_executions
        WHERE underwriting_id = %s
        """

        params = [underwriting_id]

        if processor_name:
            query += " AND processor = %s"
            params.append(processor_name)

        if status:
            query += " AND status = %s"
            params.append(status)

        query += " ORDER BY created_at DESC"

        try:
            cursor = self.db.cursor()
            cursor.execute(query, params)
            results = cursor.fetchall()
            cursor.close()
            return [dict(row) for row in results] if results else []
        except Exception as e:
            print(f"Error fetching executions by underwriting: {e}")
            return []

    # =========================================================================
    # SUPERSESSION MANAGEMENT
    # =========================================================================

    def mark_execution_superseded(
        self,
        old_execution_id: str,
        new_execution_id: str
    ) -> bool:
        """
        Mark an execution as superseded by a newer execution.

        Sets the updated_execution_id to point to the new execution.

        Args:
            old_execution_id: Original execution UUID
            new_execution_id: New execution UUID that supersedes the old one

        Returns:
            True if update successful
        """
        query = """
        UPDATE processor_executions
        SET
            updated_execution_id = %s,
            updated_at = %s
        WHERE id = %s
        """
        # TODO: Execute update with db connection
        # self.db.execute(query, (new_execution_id, datetime.utcnow(), old_execution_id))
        # return True
        return False

    def get_execution_chain(
        self,
        execution_id: str
    ) -> list[dict[str, Any]]:
        """
        Get the full chain of executions (original -> updates).

        Follows the updated_execution_id links to build the complete history.

        Args:
            execution_id: Starting execution UUID

        Returns:
            List of execution records in chronological order
        """
        # TODO: Implement recursive query or loop to follow chain
        # For now, return single execution
        execution = self.get_execution_by_id(execution_id)
        return [execution] if execution else []

    # =========================================================================
    # ACTIVATION/DEACTIVATION
    # =========================================================================

    def activate_execution(
        self,
        execution_id: str
    ) -> bool:
        """
        Activate an execution (set enabled = true).

        Args:
            execution_id: Execution UUID

        Returns:
            True if activation successful
        """
        query = """
        UPDATE processor_executions
        SET
            enabled = true,
            updated_at = %s
        WHERE id = %s
        """
        # TODO: Execute update with db connection
        # self.db.execute(query, (datetime.utcnow(), execution_id))
        # return True
        return False

    def deactivate_execution(
        self,
        execution_id: str
    ) -> bool:
        """
        Deactivate an execution (set enabled = false).

        Args:
            execution_id: Execution UUID

        Returns:
            True if deactivation successful
        """
        query = """
        UPDATE processor_executions
        SET
            enabled = false,
            disabled_at = %s,
            updated_at = %s
        WHERE id = %s
        """
        # TODO: Execute update with db connection
        # self.db.execute(query, (datetime.utcnow(), datetime.utcnow(), execution_id))
        # return True
        return False

    # =========================================================================
    # HELPER METHODS
    # =========================================================================

    def _generate_uuid(self) -> str:
        """Generate a UUID for new records."""
        import uuid
        return str(uuid.uuid4())

    def get_execution_count(
        self,
        underwriting_id: str,
        processor_name: Optional[str] = None
    ) -> int:
        """
        Get count of executions for an underwriting.

        Args:
            underwriting_id: Underwriting UUID
            processor_name: Optional filter by processor

        Returns:
            Count of executions
        """
        query = """
        SELECT COUNT(*) as count
        FROM processor_executions
        WHERE underwriting_id = %s
        """

        params = [underwriting_id]

        if processor_name:
            query += " AND processor = %s"
            params.append(processor_name)

        # TODO: Execute query with db connection
        # result = self.db.execute(query, params).fetchone()
        # return result['count'] if result else 0
        return 0

