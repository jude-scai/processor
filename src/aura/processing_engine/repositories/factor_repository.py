"""
Factor Repository

Handles factor storage and retrieval operations for the AURA underwriting system.
"""

import json
from datetime import datetime
from typing import Any, Optional
from psycopg2.extras import Json


def _json_serial(obj):
    """JSON serializer for objects not serializable by default."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")


class FactorRepository:
    """
    Repository for factor database operations.

    Manages:
    - Factor creation and updates
    - Factor consolidation and lineage tracking
    - Factor snapshots for audit trails
    """

    _instance = None
    _db_connection = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(FactorRepository, cls).__new__(cls)
        return cls._instance

    def __init__(self, db_connection: Any = None):
        """
        Initialize the repository with a database connection.

        Args:
            db_connection: Database connection or session (PostgreSQL/BigQuery)
        """
        if db_connection is not None:
            self._db_connection = db_connection
        self.db = self._db_connection

    def _generate_uuid(self) -> str:
        """Generate a UUID string."""
        import uuid

        return str(uuid.uuid4())

    def save_factors(
        self,
        organization_id: str,
        underwriting_id: str,
        underwriting_processor_id: str,
        execution_id: Optional[str],
        factors: dict[str, Any],
        source: str = "processor",
        created_by: Optional[str] = None,
    ) -> bool:
        """
        Save consolidated factors to the factor table.

        Args:
            organization_id: Organization UUID
            underwriting_id: Underwriting UUID
            underwriting_processor_id: Underwriting processor UUID
            execution_id: Execution UUID (optional)
            factors: Dictionary of factor_key -> factor_value
            source: Factor source ('processor' or 'manual')
            created_by: User who created the factors

        Returns:
            True if save successful
        """
        try:
            cursor = self.db.cursor()
            now = datetime.utcnow()

            # Process each factor with UPSERT logic
            for factor_key, factor_value in factors.items():
                print(f"    🔍 Processing factor: {factor_key} = {factor_value}")
                if factor_value is None:  # Skip None values
                    print(f"    ⏭️  Skipping {factor_key} - None value")
                    continue

                # Generate factor hash for deduplication
                factor_hash = f"{factor_key}:{json.dumps(factor_value, sort_keys=True)}"

                # Check if factor with same key and execution_id already exists
                cursor.execute(
                    """
                    SELECT id, value, factor_hash
                    FROM factor 
                    WHERE underwriting_id = %s 
                      AND factor_key = %s 
                      AND execution_id = %s
                      AND status = 'active'
                    """,
                    (underwriting_id, factor_key, execution_id),
                )
                existing_factor = cursor.fetchone()

                if existing_factor:
                    # Factor exists - check if value has changed
                    existing_id = existing_factor["id"]
                    existing_value = existing_factor["value"]
                    existing_hash = existing_factor["factor_hash"]

                    print(
                        f"    🔍 Existing factor found: {factor_key} with ID: {existing_id}"
                    )

                    if existing_hash == factor_hash:
                        # Same value, no update needed
                        print(f"    ⏭️  Skipping {factor_key} - same value")
                        continue
                    else:
                        # Value changed - update existing factor
                        print(f"    🔄 Updating {factor_key} - value changed")
                        cursor.execute(
                            """
                            UPDATE factor 
                            SET value = %s, 
                                factor_hash = %s,
                                updated_at = %s, 
                                updated_by = %s
                            WHERE id = %s
                            """,
                            (
                                Json(factor_value),
                                factor_hash,
                                now,
                                created_by,
                                existing_id,
                            ),
                        )
                else:
                    # Factor doesn't exist - insert new one
                    factor_id = self._generate_uuid()
                    print(f"    ➕ Inserting new factor: {factor_key}")

                    cursor.execute(
                        """
                        INSERT INTO factor (
                            id,
                            organization_id,
                            underwriting_id,
                            factor_key,
                            value,
                            source,
                            status,
                            factor_hash,
                            underwriting_processor_id,
                            execution_id,
                            created_by,
                            created_at,
                            updated_at
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                        )
                        """,
                        (
                            factor_id,
                            organization_id,
                            underwriting_id,
                            factor_key,
                            Json(factor_value),
                            source,
                            "active",
                            factor_hash,
                            underwriting_processor_id,
                            execution_id,
                            created_by,
                            now,
                            now,
                        ),
                    )

            self.db.commit()
            cursor.close()
            return True

        except Exception as e:
            print(f"Error saving factors: {e}")
            print(f"Exception type: {type(e)}")
            import traceback

            print(f"Traceback: {traceback.format_exc()}")
            self.db.rollback()
            return False

    def get_factors(
        self,
        underwriting_id: str,
        underwriting_processor_id: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """
        Get active factors for an underwriting.

        Args:
            underwriting_id: Underwriting UUID
            underwriting_processor_id: Optional processor filter

        Returns:
            List of factor records
        """
        try:
            cursor = self.db.cursor()

            if underwriting_processor_id:
                cursor.execute(
                    """
                    SELECT 
                        id, factor_key, value, unit, source, status,
                        underwriting_processor_id, execution_id,
                        created_at, updated_at
                    FROM factor
                    WHERE underwriting_id = %s 
                      AND underwriting_processor_id = %s
                      AND status = 'active'
                    ORDER BY created_at DESC
                    """,
                    (underwriting_id, underwriting_processor_id),
                )
            else:
                cursor.execute(
                    """
                    SELECT 
                        id, factor_key, value, unit, source, status,
                        underwriting_processor_id, execution_id,
                        created_at, updated_at
                    FROM factor
                    WHERE underwriting_id = %s 
                      AND status = 'active'
                    ORDER BY created_at DESC
                    """,
                    (underwriting_id,),
                )

            results = cursor.fetchall()
            cursor.close()

            # Convert to list of dictionaries
            factors = []
            for row in results:
                factors.append(
                    {
                        "id": row[0],
                        "factor_key": row[1],
                        "value": row[2],
                        "unit": row[3],
                        "source": row[4],
                        "status": row[5],
                        "underwriting_processor_id": row[6],
                        "execution_id": row[7],
                        "created_at": row[8],
                        "updated_at": row[9],
                    }
                )

            return factors

        except Exception as e:
            print(f"Error fetching factors: {e}")
            return []

    def clear_factors(
        self,
        underwriting_id: str,
        underwriting_processor_id: str,
        updated_by: Optional[str] = None,
    ) -> bool:
        """
        Clear all factors for a specific processor.

        Args:
            underwriting_id: Underwriting UUID
            underwriting_processor_id: Underwriting processor UUID
            updated_by: User performing the clear

        Returns:
            True if clear successful
        """
        try:
            cursor = self.db.cursor()
            now = datetime.utcnow()

            cursor.execute(
                """
                UPDATE factor 
                SET status = 'deleted', updated_at = %s, updated_by = %s
                WHERE underwriting_id = %s 
                  AND underwriting_processor_id = %s 
                  AND status = 'active'
                """,
                (now, updated_by, underwriting_id, underwriting_processor_id),
            )

            self.db.commit()
            cursor.close()
            return True

        except Exception as e:
            print(f"Error clearing factors: {e}")
            self.db.rollback()
            return False
