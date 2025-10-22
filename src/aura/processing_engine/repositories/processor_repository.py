"""
Processor Repository

Handles database operations for processor configuration and management:
- Fetch processor configurations
- Get purchased/enabled processors
- Manage processor subscriptions
- Retrieve processor metadata
"""

from typing import Any, Optional
from datetime import datetime


class ProcessorRepository:
    """
    Repository for processor-related database operations.

    This repository provides data access methods for:
    - System processor catalog
    - Tenant processor subscriptions (purchased_processors)
    - Underwriting processor configurations (underwriting_processors)
    """

    def __init__(self, db_connection: Any):
        """
        Initialize the repository with a database connection.

        Args:
            db_connection: Database connection or session (PostgreSQL/BigQuery)
        """
        self.db = db_connection

    # =========================================================================
    # SYSTEM PROCESSOR CATALOG
    # =========================================================================

    def get_processor_catalog(self) -> list[dict[str, Any]]:
        """
        Get list of all available processors in the system catalog.

        This is code-based, not database-based. In a real implementation,
        this would scan the processors directory or maintain a registry.

        Returns:
            List of processor metadata dictionaries
        """
        # TODO: Implement processor scanning/registry
        # For now, return empty list as this is code-managed
        return []

    # =========================================================================
    # PURCHASED PROCESSORS (Tenant Level)
    # =========================================================================

    def get_purchased_processor_by_id(
        self,
        purchased_processor_id: str
    ) -> Optional[dict[str, Any]]:
        """
        Get a specific purchased processor by ID.

        Args:
            purchased_processor_id: UUID of the purchased processor

        Returns:
            Purchased processor record or None if not found
        """
        query = """
        SELECT
            id,
            organization_id,
            processor,
            name,
            auto,
            status,
            config,
            price_amount,
            price_unit,
            price_currency,
            purchased_at,
            purchased_by
        FROM purchased_processors
        WHERE id = %s AND status != 'deleted'
        """
        # TODO: Execute query with db connection
        # return self.db.execute(query, (purchased_processor_id,)).fetchone()
        return None

    def get_purchased_processors_by_organization(
        self,
        organization_id: str,
        enabled_only: bool = False,
        auto_only: bool = False
    ) -> list[dict[str, Any]]:
        """
        Get all purchased processors for an organization.

        Args:
            organization_id: Organization UUID
            enabled_only: If True, only return enabled processors
            auto_only: If True, only return processors with auto=true

        Returns:
            List of purchased processor records
        """
        query = """
        SELECT
            id,
            organization_id,
            processor,
            name,
            auto,
            status,
            config,
            price_amount,
            price_unit,
            price_currency,
            purchased_at,
            purchased_by
        FROM purchased_processors
        WHERE organization_id = %s
        """

        conditions = ["status = 'active'"] if enabled_only else ["status != 'deleted'"]
        if auto_only:
            conditions.append("auto = true")

        if conditions:
            query += " AND " + " AND ".join(conditions)

        # TODO: Execute query with db connection
        # return self.db.execute(query, (organization_id,)).fetchall()
        return []

    # =========================================================================
    # UNDERWRITING PROCESSORS (Underwriting Level)
    # =========================================================================

    def get_underwriting_processor_by_id(
        self,
        underwriting_processor_id: str
    ) -> Optional[dict[str, Any]]:
        """
        Get a specific underwriting processor configuration.

        Args:
            underwriting_processor_id: UUID of underwriting processor

        Returns:
            Underwriting processor record or None
        """
        query = """
        SELECT
            up.id,
            up.organization_id,
            up.underwriting_id,
            up.purchased_processor_id,
            up.processor,
            up.name,
            up.auto,
            up.enabled,
            up.config_override,
            up.effective_config,
            up.current_executions_list,
            pp.config as purchased_config,
            pp.price_amount,
            pp.price_unit
        FROM underwriting_processors up
        LEFT JOIN purchased_processors pp ON up.purchased_processor_id = pp.id
        WHERE up.id = %s AND up.enabled = true
        """
        # TODO: Execute query with db connection
        # return self.db.execute(query, (underwriting_processor_id,)).fetchone()
        return None

    def get_underwriting_processors(
        self,
        underwriting_id: str,
        enabled_only: bool = True,
        auto_only: bool = False
    ) -> list[dict[str, Any]]:
        """
        Get all processors configured for an underwriting.

        Args:
            underwriting_id: Underwriting UUID
            enabled_only: If True, only return enabled processors
            auto_only: If True, only return auto-execution processors

        Returns:
            List of underwriting processor configurations
        """
        query = """
        SELECT
            up.id,
            up.organization_id,
            up.underwriting_id,
            up.purchased_processor_id,
            up.processor,
            up.name,
            up.auto,
            up.enabled,
            up.config_override,
            up.effective_config,
            up.current_executions_list,
            pp.config as purchased_config,
            pp.price_amount,
            pp.price_unit
        FROM underwriting_processors up
        LEFT JOIN purchased_processors pp ON up.purchased_processor_id = pp.id
        WHERE up.underwriting_id = %s
        """

        conditions = []
        if enabled_only:
            conditions.append("up.enabled = true")
        if auto_only:
            conditions.append("up.auto = true")

        if conditions:
            query += " AND " + " AND ".join(conditions)

        query += " ORDER BY up.created_at"

        # TODO: Execute query with db connection
        # return self.db.execute(query, (underwriting_id,)).fetchall()
        return []

    def update_current_executions_list(
        self,
        underwriting_processor_id: str,
        execution_ids: list[str]
    ) -> bool:
        """
        Update the current executions list for an underwriting processor.

        Args:
            underwriting_processor_id: UUID of underwriting processor
            execution_ids: List of execution IDs to set as current

        Returns:
            True if update successful
        """
        query = """
        UPDATE underwriting_processors
        SET
            current_executions_list = %s,
            updated_at = %s
        WHERE id = %s
        """
        # TODO: Execute update with db connection
        # self.db.execute(query, (execution_ids, datetime.utcnow(), underwriting_processor_id))
        # return True
        return False

    # =========================================================================
    # PROCESSOR CONFIGURATION HELPERS
    # =========================================================================

    def get_effective_config(
        self,
        underwriting_processor_id: str
    ) -> dict[str, Any]:
        """
        Get the effective configuration for an underwriting processor.

        Merges:
        1. Processor default CONFIG (from code)
        2. Purchased processor config (tenant overrides)
        3. Underwriting processor config_override (case-specific)

        Args:
            underwriting_processor_id: UUID of underwriting processor

        Returns:
            Merged configuration dictionary
        """
        processor_record = self.get_underwriting_processor_by_id(underwriting_processor_id)
        if not processor_record:
            return {}

        # Start with purchased processor config
        config = processor_record.get("purchased_config", {}) or {}

        # Apply underwriting-specific overrides
        overrides = processor_record.get("config_override", {}) or {}
        config.update(overrides)

        return config

    def get_processor_by_name(
        self,
        processor_name: str,
        organization_id: str
    ) -> Optional[dict[str, Any]]:
        """
        Get a purchased processor by processor name and organization.

        Args:
            processor_name: Processor identifier (e.g., 'p_bank_statement')
            organization_id: Organization UUID

        Returns:
            Purchased processor record or None
        """
        query = """
        SELECT
            id,
            organization_id,
            processor,
            name,
            auto,
            status,
            config,
            price_amount,
            price_unit,
            price_currency
        FROM purchased_processors
        WHERE processor = %s
          AND organization_id = %s
          AND status = 'active'
        LIMIT 1
        """
        # TODO: Execute query with db connection
        # return self.db.execute(query, (processor_name, organization_id)).fetchone()
        return None

