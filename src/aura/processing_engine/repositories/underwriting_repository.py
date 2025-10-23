"""
Underwriting Repository

Handles database operations for underwriting data and owners:
- Save application form data
- Manage owners list (INSERT/UPDATE/SOFT DELETE)
- Update underwriting records with processor output
"""

from typing import Any, Optional
from datetime import datetime
import json


class UnderwritingRepository:
    """
    Repository for underwriting and owner data persistence.
    
    This repository provides data access methods for:
    - Application form data (underwritings table)
    - Owners list management (owners table)
    - Coordinated updates from processor outputs
    """
    
    def __init__(self, db_connection: Any):
        """
        Initialize the repository with a database connection.
        
        Args:
            db_connection: Database connection or session (PostgreSQL/BigQuery)
        """
        self.db = db_connection
    
    # =========================================================================
    # APPLICATION FORM PERSISTENCE
    # =========================================================================
    
    def save_application_form(
        self,
        underwriting_id: str,
        form_data: dict[str, Any],
        merge: bool = True
    ) -> bool:
        """
        Save or update application form data.
        
        Args:
            underwriting_id: The underwriting ID
            form_data: Dictionary with dot-notation keys (e.g., "merchant.ein")
            merge: If True, merge with existing data; if False, replace completely
            
        Returns:
            True if successful, False otherwise
            
        Example:
            form_data = {
                "merchant.name": "ABC Tech Inc",
                "merchant.ein": "12-3456789",
                "merchant.industry": "Technology"
            }
        """
        try:
            if merge:
                # Get existing application form
                cursor = self.db.cursor()
                cursor.execute("""
                    SELECT application_form 
                    FROM underwritings 
                    WHERE id = %s
                """, (underwriting_id,))
                
                result = cursor.fetchone()
                existing_form = result['application_form'] if result else {}
                
                # Merge new data with existing (new data takes precedence)
                merged_form = {**existing_form, **form_data}
                form_to_save = merged_form
            else:
                # Replace completely
                form_to_save = form_data
            
            # Update underwriting record
            cursor = self.db.cursor()
            cursor.execute("""
                UPDATE underwritings 
                SET application_form = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """, (json.dumps(form_to_save), underwriting_id))
            
            self.db.commit()
            return True
            
        except Exception as e:
            self.db.rollback()
            print(f"Error saving application form: {e}")
            return False
    
    # =========================================================================
    # OWNERS LIST MANAGEMENT
    # =========================================================================
    
    def save_owners_list(
        self,
        underwriting_id: str,
        owners_list: list[dict[str, Any]],
        created_by: Optional[str] = None,
        updated_by: Optional[str] = None
    ) -> dict[str, list[str]]:
        """
        Save owners list with automatic INSERT/UPDATE/SOFT DELETE logic.
        
        Logic:
        - If owner has owner_id and exists in DB: UPDATE
        - If owner has no owner_id: INSERT new owner
        - If existing owner not in input list: SOFT DELETE (enabled = false)
        
        Args:
            underwriting_id: The underwriting ID
            owners_list: List of owner dictionaries from processor output
            created_by: User ID for created_by field (optional)
            updated_by: User ID for updated_by field (optional)
            
        Returns:
            Dictionary with lists of inserted, updated, and removed owner IDs
            
        Example:
            owners_list = [
                {
                    "owner_id": "owner_001",  # Existing - will UPDATE
                    "first_name": "John",
                    "last_name": "Doe",
                    "email": "john@example.com",
                    "ownership_percent": 60.0
                },
                {
                    "owner_id": None,  # New - will INSERT
                    "first_name": "Jane",
                    "last_name": "Smith",
                    "email": "jane@example.com",
                    "ownership_percent": 40.0
                }
            ]
        """
        operations = {
            'inserted': [],
            'updated': [],
            'removed': []
        }
        
        try:
            cursor = self.db.cursor()
            
            # Step 1: Get existing owner IDs from database
            cursor.execute("""
                SELECT owner_id 
                FROM owners 
                WHERE underwriting_id = %s AND enabled = true
            """, (underwriting_id,))
            
            existing_owner_ids = {row['owner_id'] for row in cursor.fetchall()}
            
            # Step 2: Extract owner IDs from input
            input_owner_ids = {
                owner['owner_id'] 
                for owner in owners_list 
                if owner.get('owner_id') is not None
            }
            
            # Step 3: Calculate removed owners
            removed_owner_ids = existing_owner_ids - input_owner_ids
            
            # Step 4: Process each owner in input
            for owner_data in owners_list:
                owner_id = owner_data.get('owner_id')
                
                if owner_id and owner_id in existing_owner_ids:
                    # EXISTING OWNER - UPDATE
                    cursor.execute("""
                        UPDATE owners 
                        SET first_name = %s,
                            last_name = %s,
                            email = %s,
                            phone_mobile = %s,
                            phone_home = %s,
                            phone_work = %s,
                            ssn = %s,
                            ownership_percent = %s,
                            primary_owner = %s,
                            updated_at = CURRENT_TIMESTAMP,
                            updated_by = %s
                        WHERE owner_id = %s
                    """, (
                        owner_data.get('first_name'),
                        owner_data.get('last_name'),
                        owner_data.get('email'),
                        owner_data.get('phone_mobile'),
                        owner_data.get('phone_home'),
                        owner_data.get('phone_work'),
                        owner_data.get('ssn'),
                        owner_data.get('ownership_percent'),
                        owner_data.get('primary_owner', False),
                        updated_by,
                        owner_id
                    ))
                    operations['updated'].append(owner_id)
                    
                else:
                    # NEW OWNER - INSERT
                    new_owner_id = self._generate_uuid()
                    cursor.execute("""
                        INSERT INTO owners (
                            owner_id,
                            underwriting_id,
                            first_name,
                            last_name,
                            email,
                            phone_mobile,
                            phone_home,
                            phone_work,
                            ssn,
                            ownership_percent,
                            primary_owner,
                            enabled,
                            created_at,
                            updated_at,
                            created_by,
                            updated_by
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 
                            true, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, %s, %s
                        )
                    """, (
                        new_owner_id,
                        underwriting_id,
                        owner_data.get('first_name'),
                        owner_data.get('last_name'),
                        owner_data.get('email'),
                        owner_data.get('phone_mobile'),
                        owner_data.get('phone_home'),
                        owner_data.get('phone_work'),
                        owner_data.get('ssn'),
                        owner_data.get('ownership_percent'),
                        owner_data.get('primary_owner', False),
                        created_by,
                        updated_by
                    ))
                    operations['inserted'].append(new_owner_id)
            
            # Step 5: Soft delete removed owners
            for removed_id in removed_owner_ids:
                cursor.execute("""
                    UPDATE owners 
                    SET enabled = false,
                        updated_at = CURRENT_TIMESTAMP,
                        updated_by = %s
                    WHERE owner_id = %s
                """, (updated_by, removed_id))
                operations['removed'].append(removed_id)
            
            # Commit transaction
            self.db.commit()
            return operations
            
        except Exception as e:
            self.db.rollback()
            print(f"Error saving owners list: {e}")
            raise
    
    # =========================================================================
    # COMBINED OPERATIONS
    # =========================================================================
    
    def save_processor_output(
        self,
        underwriting_id: str,
        processor_output: dict[str, Any],
        user_id: Optional[str] = None
    ) -> dict[str, Any]:
        """
        Save complete processor output (application form + owners list).
        
        This is the main method to use when saving Application Processor output.
        It handles both application form and owners list in a single transaction.
        
        Args:
            underwriting_id: The underwriting ID
            processor_output: Complete processor output with application_form and owners_list
            user_id: User ID for audit fields (optional)
            
        Returns:
            Dictionary with operation results
            
        Example:
            processor_output = {
                "application_form": {
                    "merchant.name": "ABC Tech Inc",
                    "merchant.ein": "12-3456789"
                },
                "owners_list": [
                    {"owner_id": "owner_001", "first_name": "John", ...},
                    {"owner_id": None, "first_name": "Jane", ...}
                ]
            }
            
            result = repo.save_processor_output(underwriting_id, processor_output)
            # Result:
            # {
            #   "application_form_saved": True,
            #   "owners_operations": {
            #     "inserted": ["owner_002"],
            #     "updated": ["owner_001"],
            #     "removed": []
            #   }
            # }
        """
        result = {
            "application_form_saved": False,
            "owners_operations": None,
            "error": None
        }
        
        try:
            # Save application form
            application_form = processor_output.get("application_form", {})
            if application_form:
                success = self.save_application_form(
                    underwriting_id=underwriting_id,
                    form_data=application_form,
                    merge=True
                )
                result["application_form_saved"] = success
            
            # Save owners list
            owners_list = processor_output.get("owners_list", [])
            if owners_list is not None:  # Allow empty list (removes all owners)
                operations = self.save_owners_list(
                    underwriting_id=underwriting_id,
                    owners_list=owners_list,
                    created_by=user_id,
                    updated_by=user_id
                )
                result["owners_operations"] = operations
            
            return result
            
        except Exception as e:
            result["error"] = str(e)
            return result
    
    # =========================================================================
    # HELPER METHODS
    # =========================================================================
    
    def _generate_uuid(self) -> str:
        """Generate a UUID for new records."""
        import uuid
        return f"owner_{uuid.uuid4().hex[:12]}"
    
    def get_owners(
        self,
        underwriting_id: str,
        enabled_only: bool = True
    ) -> list[dict[str, Any]]:
        """
        Get owners for an underwriting.
        
        Args:
            underwriting_id: The underwriting ID
            enabled_only: If True, only return enabled owners
            
        Returns:
            List of owner dictionaries
        """
        try:
            cursor = self.db.cursor()
            
            query = """
                SELECT owner_id, first_name, last_name, email, 
                       phone_mobile, phone_home, phone_work, ssn,
                       ownership_percent, primary_owner, enabled,
                       created_at, updated_at
                FROM owners 
                WHERE underwriting_id = %s
            """
            
            if enabled_only:
                query += " AND enabled = true"
            
            query += " ORDER BY primary_owner DESC, first_name"
            
            cursor.execute(query, (underwriting_id,))
            return cursor.fetchall()
            
        except Exception as e:
            print(f"Error fetching owners: {e}")
            return []
    
    def restore_owner(self, owner_id: str, user_id: Optional[str] = None) -> bool:
        """
        Restore a soft-deleted owner (set enabled = true).
        
        Args:
            owner_id: The owner ID to restore
            user_id: User ID for audit trail
            
        Returns:
            True if successful, False otherwise
        """
        try:
            cursor = self.db.cursor()
            cursor.execute("""
                UPDATE owners 
                SET enabled = true,
                    updated_at = CURRENT_TIMESTAMP,
                    updated_by = %s
                WHERE owner_id = %s
            """, (user_id, owner_id))
            
            self.db.commit()
            return True
            
        except Exception as e:
            self.db.rollback()
            print(f"Error restoring owner: {e}")
            return False

