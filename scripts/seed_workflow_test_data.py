"""
Workflow Test Data Seeder

Creates comprehensive test data for all 5 workflows:
- Workflow 1: Auto execution
- Workflow 2: Manual execution  
- Workflow 3: Consolidation only
- Workflow 4: Execution activation (rollback)
- Workflow 5: Execution disable

Usage:
    python scripts/seed_workflow_test_data.py
"""

import os
import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone
import uuid
import json
import hashlib

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import psycopg2
from psycopg2.extras import Json, RealDictCursor


def generate_uuid():
    return str(uuid.uuid4())


def generate_timestamp(days_ago=0, hours_ago=0):
    return datetime.now(timezone.utc) - timedelta(days=days_ago, hours=hours_ago)


def generate_payload_hash(payload, trigger_fields):
    """Generate hash from payload using trigger fields only."""
    trigger_data = {k: v for k, v in payload.items() if k in trigger_fields}
    payload_str = json.dumps(trigger_data, sort_keys=True)
    return hashlib.sha256(payload_str.encode()).hexdigest()


class WorkflowTestDataSeeder:
    """Generate test data for all workflows."""

    def __init__(self, db_conn):
        self.db_conn = db_conn
        self.cursor = db_conn.cursor()

    def seed_all(self):
        """Seed all workflow test data."""
        print("🌱 Seeding workflow test data...\n")

        self.seed_organization()
        self.seed_accounts()
        self.seed_underwritings()
        self.seed_owners()
        self.seed_merchant_addresses()
        self.seed_documents()
        self.seed_purchased_processors()
        self.seed_underwriting_processors()
        self.seed_executions()
        self.seed_factors()

        self.db_conn.commit()
        print("\n✅ Workflow test data seeded successfully!")
        self.print_summary()

    def seed_organization(self):
        """Create test organization."""
        print("📊 Creating organization...")

        self.cursor.execute(
            """
            INSERT INTO organization (id, name, status, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (id) DO NOTHING
            """,
            (
                "00000000-0000-0000-0000-000000000001",
                "Test Organization",
                "active",
                generate_timestamp(365),
                generate_timestamp(1),
            ),
        )

        self.organization_id = "00000000-0000-0000-0000-000000000001"
        print("   ✓ Organization created")

    def seed_accounts(self):
        """Create test accounts."""
        print("👤 Creating accounts...")

        account_id = "00000000-0000-0000-0000-000000000002"

        self.cursor.execute(
            """
            INSERT INTO account (
                id, organization_id, firebase_uid, email, first_name, last_name,
                status, created_at, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO NOTHING
            """,
            (
                account_id,
                self.organization_id,
                "test-firebase-uid",
                "test@example.com",
                "Test",
                "User",
                "active",
                generate_timestamp(365),
                generate_timestamp(1),
            ),
        )

        self.account_id = account_id
        print("   ✓ Test account created")

    def seed_underwritings(self):
        """Create test underwritings for all workflows."""
        print("📋 Creating underwritings...")

        underwriting_data = {
            "id": generate_uuid(),
            "serial_number": "TEST-WF-001",
            "status": "processing",
            "application_type": "NEW",
            "request_amount": 150000.00,
            "request_date": generate_timestamp(7).date(),
            "purpose": "Workflow testing",
            # Merchant details
            "merchant_name": "Test Merchant Inc",
            "merchant_dba_name": "Test Merchant",
            "merchant_email": "info@testmerchant.com",
            "merchant_phone": "555-0100",
            "merchant_website": "https://testmerchant.com",
            "merchant_industry": "5734",
            "merchant_ein": "12-3456789",
            "merchant_entity_type": "Corporation",
            "merchant_incorporation_date": (
                generate_timestamp(1095)
            ).date(),
            "merchant_state_of_incorporation": "CA",
            "merchant_ref_id": "merch_001",
        }

        self.cursor.execute(
            """
            INSERT INTO underwriting (
                id, organization_id, serial_number, status, application_type,
                request_amount, request_date, purpose,
                merchant_ref_id, merchant_name, merchant_dba_name, merchant_email,
                merchant_phone, merchant_website, merchant_industry, merchant_ein,
                merchant_entity_type, merchant_incorporation_date, merchant_state_of_incorporation,
                created_at, updated_at, created_by, updated_by
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            """,
            (
                underwriting_data["id"],
                self.organization_id,
                underwriting_data["serial_number"],
                underwriting_data["status"],
                underwriting_data["application_type"],
                underwriting_data["request_amount"],
                underwriting_data["request_date"],
                underwriting_data["purpose"],
                underwriting_data["merchant_ref_id"],
                underwriting_data["merchant_name"],
                underwriting_data["merchant_dba_name"],
                underwriting_data["merchant_email"],
                underwriting_data["merchant_phone"],
                underwriting_data["merchant_website"],
                underwriting_data["merchant_industry"],
                underwriting_data["merchant_ein"],
                underwriting_data["merchant_entity_type"],
                underwriting_data["merchant_incorporation_date"],
                underwriting_data["merchant_state_of_incorporation"],
                generate_timestamp(7),
                generate_timestamp(1),
                self.account_id,
                self.account_id,
            ),
        )

        self.underwriting_id = underwriting_data["id"]
        print(f"   ✓ Created underwriting: {self.underwriting_id}")

    def seed_owners(self):
        """Create test owners."""
        print("👨‍💼 Creating owners...")

        owner_id = generate_uuid()

        self.cursor.execute(
            """
            INSERT INTO owner (
                id, underwriting_id, first_name, last_name, email,
                phone_mobile, birthday, fico_score, ssn,
                enabled, ownership_percent, primary_owner,
                created_at, updated_at, created_by, updated_by
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                owner_id,
                self.underwriting_id,
                "John",
                "Doe",
                "john@testmerchant.com",
                "555-0101",
                generate_timestamp(15330).date(),  # ~42 years old
                720,
                "123-45-6789",
                True,
                100.0,
                True,
                generate_timestamp(7),
                generate_timestamp(1),
                self.account_id,
                self.account_id,
            ),
        )

        print("   ✓ Owner created")

    def seed_merchant_addresses(self):
        """Create merchant address."""
        print("🏠 Creating merchant address...")

        self.cursor.execute(
            """
            INSERT INTO merchant_address (
                id, underwriting_id, addr_1, city, state, zip,
                created_at, updated_at, created_by, updated_by
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                generate_uuid(),
                self.underwriting_id,
                "123 Test St",
                "San Francisco",
                "CA",
                "94105",
                generate_timestamp(7),
                generate_timestamp(1),
                self.account_id,
                self.account_id,
            ),
        )

        print("   ✓ Address created")

    def seed_documents(self):
        """Create documents for testing."""
        print("📄 Creating documents...")

        # Bank statement document
        doc1_id = generate_uuid()
        rev1_id = generate_uuid()

        self.cursor.execute(
            """
            INSERT INTO document (
                id, organization_id, underwriting_id, status, current_revision_id,
                stipulation_type, classification_confidence,
                created_at, created_by, updated_at, updated_by
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                doc1_id,
                self.organization_id,
                self.underwriting_id,
                "accepted",
                rev1_id,
                "s_bank_statement",
                0.95,
                generate_timestamp(7),
                self.account_id,
                generate_timestamp(1),
                self.account_id,
            ),
        )

        self.cursor.execute(
            """
            INSERT INTO document_revision (
                id, document_id, revision, gcs_uri, filename, mime_type,
                size_bytes, quality_score, page_count,
                created_at, created_by, updated_at, updated_by
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                rev1_id,
                doc1_id,
                1,
                f"gs://test-bucket/documents/{rev1_id}.pdf",
                "bank_statement_jan.pdf",
                "application/pdf",
                1024000,
                0.92,
                2,
                generate_timestamp(7),
                self.account_id,
                generate_timestamp(1),
                self.account_id,
            ),
        )

        # Driver's license document
        doc2_id = generate_uuid()
        rev2_id = generate_uuid()

        self.cursor.execute(
            """
            INSERT INTO document (
                id, organization_id, underwriting_id, status, current_revision_id,
                stipulation_type, classification_confidence,
                created_at, created_by, updated_at, updated_by
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                doc2_id,
                self.organization_id,
                self.underwriting_id,
                "accepted",
                rev2_id,
                "s_drivers_license",
                0.98,
                generate_timestamp(7),
                self.account_id,
                generate_timestamp(1),
                self.account_id,
            ),
        )

        self.cursor.execute(
            """
            INSERT INTO document_revision (
                id, document_id, revision, gcs_uri, filename, mime_type,
                size_bytes, quality_score, page_count,
                created_at, created_by, updated_at, updated_by
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                rev2_id,
                doc2_id,
                1,
                f"gs://test-bucket/documents/{rev2_id}.png",
                "drivers_license.jpg",
                "image/png",
                512000,
                0.95,
                1,
                generate_timestamp(7),
                self.account_id,
                generate_timestamp(1),
                self.account_id,
            ),
        )

        # Store for later use
        self.document_ids = [doc1_id, doc2_id]
        self.revision_ids = [rev1_id, rev2_id]

        print(f"   ✓ Created {len(self.document_ids)} documents")

    def seed_purchased_processors(self):
        """Create purchased processors."""
        print("🔧 Creating purchased processors...")

        processors = [
            {
                "processor": "test_application_processor",
                "name": "Test Application Processor",
                "auto": True,
                "config": {
                    "processor_type": "APPLICATION",
                    "triggers": {
                        "application_form": ["merchant.name", "merchant.ein"]
                    },
                },
            },
            {
                "processor": "test_bank_statement_processor",
                "name": "Test Bank Statement Processor",
                "auto": True,
                "config": {
                    "processor_type": "STIPULATION",
                    "stipulation_type": "s_bank_statement",
                    "triggers": {
                        "documents_list": ["s_bank_statement"]
                    },
                },
            },
            {
                "processor": "test_drivers_license_processor",
                "name": "Test Driver's License Processor",
                "auto": False,  # Manual only for testing
                "config": {
                    "processor_type": "DOCUMENT",
                    "stipulation_type": "s_drivers_license",
                    "triggers": {
                        "documents_list": ["s_drivers_license"]
                    },
                },
            },
        ]

        self.purchased_processors = []

        for proc in processors:
            proc_id = generate_uuid()

            self.cursor.execute(
                """
                INSERT INTO organization_processors (
                    id, organization_id, processor, name, auto, status, config,
                    price_amount, price_unit, price_currency,
                    purchased_at, purchased_by
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    proc_id,
                    self.organization_id,
                    proc["processor"],
                    proc["name"],
                    proc["auto"],
                    "active",
                    Json(proc["config"]),
                    100,  # $1.00
                    "execution",
                    "USD",
                    generate_timestamp(60),
                    self.account_id,
                ),
            )

            self.purchased_processors.append({
                **proc,
                "id": proc_id,
            })

        print(f"   ✓ Created {len(self.purchased_processors)} purchased processors")

    def seed_underwriting_processors(self):
        """Create underwriting processor configurations."""
        print("⚙️  Creating underwriting processor configurations...")

        self.underwriting_processors = []

        for proc in self.purchased_processors:
            up_id = generate_uuid()

            self.cursor.execute(
                """
                INSERT INTO underwriting_processors (
                    id, organization_id, underwriting_id, organization_processor_id,
                    processor, name, auto, enabled, config_override, effective_config,
                    current_executions_list, created_at, created_by, updated_at, updated_by
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::uuid[], %s, %s, %s, %s)
                """,
                (
                    up_id,
                    self.organization_id,
                    self.underwriting_id,
                    proc["id"],
                    proc["processor"],
                    proc["name"],
                    proc["auto"],
                    True,  # enabled
                    Json({}),
                    Json(proc["config"]),
                    [],  # current_executions_list
                    generate_timestamp(7),
                    self.account_id,
                    generate_timestamp(1),
                    self.account_id,
                ),
            )

            self.underwriting_processors.append({
                **proc,
                "underwriting_processor_id": up_id,
            })

        print(f"   ✓ Created {len(self.underwriting_processors)} underwriting processor configs")

    def seed_executions(self):
        """Create test executions for all workflows."""
        print("🔄 Creating executions...")

        # Execution for Workflow 1 (completed)
        exec1_id = generate_uuid()
        exec1_payload = {
            "underwriting_id": self.underwriting_id,
            "application_form": {
                "merchant.name": "Test Merchant Inc",
                "merchant.ein": "12-3456789",
            },
            "owners_list": [],
            "documents_list": [],
        }
        exec1_hash = generate_payload_hash(exec1_payload, ["merchant.name", "merchant.ein"])

        self.cursor.execute(
            """
            INSERT INTO processor_executions (
                id, organization_id, underwriting_id, underwriting_processor_id,
                processor, status, enabled, payload, payload_hash, factors_delta,
                run_cost_cents, currency, started_at, completed_at,
                created_at, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                exec1_id,
                self.organization_id,
                self.underwriting_id,
                self.underwriting_processors[0]["underwriting_processor_id"],
                "test_application_processor",
                "completed",
                True,
                Json(exec1_payload),
                exec1_hash,
                Json({"factors": {"merchant.name": "Test Merchant Inc", "merchant.verified": True}}),
                500,
                "USD",
                generate_timestamp(5),
                generate_timestamp(5),
                generate_timestamp(5),
                generate_timestamp(5),
            ),
        )

        # Execution for Workflow 2 (pending) - Manual execution
        exec2_id = generate_uuid()
        exec2_payload = {
            "underwriting_id": self.underwriting_id,
            "revision_id": self.revision_ids[0],  # Bank statement revision
        }
        exec2_hash = generate_payload_hash(exec2_payload, ["revision_id"])

        self.cursor.execute(
            """
            INSERT INTO processor_executions (
                id, organization_id, underwriting_id, underwriting_processor_id,
                processor, status, enabled, payload, payload_hash,
                run_cost_cents, currency,
                created_at, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                exec2_id,
                self.organization_id,
                self.underwriting_id,
                self.underwriting_processors[1]["underwriting_processor_id"],
                "test_bank_statement_processor",
                "pending",
                True,
                Json(exec2_payload),
                exec2_hash,
                250,
                "USD",
                generate_timestamp(1),
                generate_timestamp(1),
            ),
        )

        # Execution for Workflow 4 (completed) - For activation/rollback
        exec3_id = generate_uuid()
        exec3_payload = {
            "underwriting_id": self.underwriting_id,
            "application_form": {
                "merchant.name": "Old Merchant Name",
                "merchant.ein": "99-9999999",
            },
            "revision_id": self.revision_ids,
        }
        exec3_hash = generate_payload_hash(exec3_payload, ["merchant.name", "merchant.ein"])

        self.cursor.execute(
            """
            INSERT INTO processor_executions (
                id, organization_id, underwriting_id, underwriting_processor_id,
                processor, status, enabled, payload, payload_hash, factors_delta,
                run_cost_cents, currency, started_at, completed_at,
                created_at, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                exec3_id,
                self.organization_id,
                self.underwriting_id,
                self.underwriting_processors[0]["underwriting_processor_id"],
                "test_application_processor",
                "completed",
                True,
                Json(exec3_payload),
                exec3_hash,
                Json({"factors": {"merchant.name": "Old Merchant Name"}}),
                500,
                "USD",
                generate_timestamp(10),
                generate_timestamp(10),
                generate_timestamp(10),
                generate_timestamp(10),
            ),
        )

        # Execution for Workflow 5 (completed) - For disable testing
        exec4_id = generate_uuid()
        exec4_payload = {
            "underwriting_id": self.underwriting_id,
            "revision_id": self.revision_ids[1],  # Driver's license
        }
        exec4_hash = generate_payload_hash(exec4_payload, ["revision_id"])

        self.cursor.execute(
            """
            INSERT INTO processor_executions (
                id, organization_id, underwriting_id, underwriting_processor_id,
                processor, status, enabled, payload, payload_hash, factors_delta,
                run_cost_cents, currency, started_at, completed_at,
                created_at, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                exec4_id,
                self.organization_id,
                self.underwriting_id,
                self.underwriting_processors[2]["underwriting_processor_id"],
                "test_drivers_license_processor",
                "completed",
                True,
                Json(exec4_payload),
                exec4_hash,
                Json({"factors": {"license.verified": True, "license.state": "CA"}}),
                150,
                "USD",
                generate_timestamp(8),
                generate_timestamp(8),
                generate_timestamp(8),
                generate_timestamp(8),
            ),
        )

        # Store execution IDs for summary
        self.execution_ids = {
            "workflow1": exec1_id,
            "workflow2": exec2_id,
            "workflow4": exec3_id,
            "workflow5": exec4_id,
        }

        # Update current_executions_list
        self.cursor.execute(
            """
            UPDATE underwriting_processors
            SET current_executions_list = %s::uuid[]
            WHERE id = %s
            """,
            ([exec1_id], self.underwriting_processors[0]["underwriting_processor_id"]),
        )

        self.cursor.execute(
            """
            UPDATE underwriting_processors
            SET current_executions_list = %s::uuid[]
            WHERE id = %s
            """,
            ([exec4_id], self.underwriting_processors[2]["underwriting_processor_id"]),
        )

        print(f"   ✓ Created {len(self.execution_ids)} test executions")

    def seed_factors(self):
        """Create factors."""
        print("📊 Creating factors...")

        # Factors from execution 1
        self.cursor.execute(
            """
            INSERT INTO factor (
                id, organization_id, underwriting_id, factor_key, value, unit,
                source, status, underwriting_processor_id, execution_id,
                created_at, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                generate_uuid(),
                self.organization_id,
                self.underwriting_id,
                "merchant.name",
                Json("Test Merchant Inc"),
                None,
                "processor",
                "active",
                self.underwriting_processors[0]["underwriting_processor_id"],
                self.execution_ids["workflow1"],
                generate_timestamp(5),
                generate_timestamp(5),
            ),
        )

        self.cursor.execute(
            """
            INSERT INTO factor (
                id, organization_id, underwriting_id, factor_key, value, unit,
                source, status, underwriting_processor_id, execution_id,
                created_at, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                generate_uuid(),
                self.organization_id,
                self.underwriting_id,
                "merchant.verified",
                Json(True),
                None,
                "processor",
                "active",
                self.underwriting_processors[0]["underwriting_processor_id"],
                self.execution_ids["workflow1"],
                generate_timestamp(5),
                generate_timestamp(5),
            ),
        )

        print("   ✓ Factors created")

    def print_summary(self):
        """Print summary of test data."""
        print("\n" + "=" * 70)
        print("📊 WORKFLOW TEST DATA SUMMARY")
        print("=" * 70)
        print(f"\n📍 Underwriting ID: {self.underwriting_id}")
        print(f"📝 Serial Number: TEST-WF-001")
        print(f"\n🔧 Processors:")
        for i, proc in enumerate(self.underwriting_processors, 1):
            print(f"   {i}. {proc['name']}")
            print(f"      ID: {proc['underwriting_processor_id']}")
            print(f"      Processor: {proc['processor']}")
            print(f"      Auto: {proc['auto']}")
            print(f"      Enabled: True")

        print(f"\n🔄 Test Executions:")
        print(f"   Workflow 1 (Auto): {self.execution_ids['workflow1']}")
        print(f"   Workflow 2 (Manual - Pending): {self.execution_ids['workflow2']}")
        print(f"   Workflow 4 (Activation): {self.execution_ids['workflow4']}")
        print(f"   Workflow 5 (Disable): {self.execution_ids['workflow5']}")

        print(f"\n📄 Documents: {len(self.document_ids)}")
        print(f"📊 Revision IDs: {len(self.revision_ids)}")

        print("\n" + "=" * 70)
        print("\n🧪 WORKFLOW TESTING GUIDE")
        print("=" * 70)
        print("\n1️⃣  Workflow 1 (Auto Execution):")
        print(f"   Send message to 'underwriting.updated' with:")
        print(f'   {{"underwriting_id": "{self.underwriting_id}"}}')

        print("\n2️⃣  Workflow 2 (Manual Execution):")
        print(f"   Send message to 'underwriting.processor.execute' with:")
        print(f'   {{"underwriting_processor_id": "{self.underwriting_processors[1]["underwriting_processor_id"]}"}}')

        print("\n3️⃣  Workflow 3 (Consolidation):")
        print(f"   Send message to 'underwriting.processor.consolidation' with:")
        print(f'   {{"underwriting_processor_id": "{self.underwriting_processors[0]["underwriting_processor_id"]}"}}')

        print("\n4️⃣  Workflow 4 (Activation/Rollback):")
        print(f"   Send message to 'underwriting.execution.activate' with:")
        print(f'   {{"execution_id": "{self.execution_ids["workflow4"]}"}}')

        print("\n5️⃣  Workflow 5 (Disable):")
        print(f"   Send message to 'underwriting.execution.disable' with:")
        print(f'   {{"execution_id": "{self.execution_ids["workflow5"]}"}}')

        print("\n" + "=" * 70)

    def clear_existing_data(self):
        """Clear existing test data."""
        print("🗑️  Clearing existing test data...")

        tables = [
            "factor",
            "processor_executions",
            "document_revision",
            "document",
            "underwriting_processors",
            "organization_processors",
            "owner_address",
            "owner",
            "merchant_address",
            "underwriting",
        ]

        for table in tables:
            self.cursor.execute(f"TRUNCATE TABLE {table} CASCADE;")

        print("   ✓ Existing data cleared")


def main():
    """Main entry point."""
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║                                                              ║")
    print("║   🌱 Workflow Test Data Seeder 🌱                           ║")
    print("║                                                              ║")
    print("╚══════════════════════════════════════════════════════════════╝")

    # Connect to database
    print("\n🔌 Connecting to PostgreSQL...")
    try:
        db_conn = psycopg2.connect(
            host=os.getenv("POSTGRES_HOST", "localhost"),
            port=int(os.getenv("POSTGRES_PORT", "5432")),
            database=os.getenv("POSTGRES_DB", "aura_underwriting"),
            user=os.getenv("POSTGRES_USER", "aura_user"),
            password=os.getenv("POSTGRES_PASSWORD", "aura_password"),
        )
        print("   ✓ Connected to PostgreSQL")
    except Exception as e:
        print(f"   ❌ Connection failed: {e}")
        print("   💡 Make sure Docker services are running: docker compose up -d")
        sys.exit(1)

    seeder = WorkflowTestDataSeeder(db_conn)

    # Ask if user wants to clear existing data
    response = input("\n🗑️  Clear existing test data first? (y/N): ").strip().lower()
    if response == "y":
        seeder.clear_existing_data()

    seeder.seed_all()
    db_conn.close()
    print("\n✨ Workflow test data ready!\n")


if __name__ == "__main__":
    main()

