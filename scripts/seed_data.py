"""
Database Seeder for AURA Underwriting System

Creates mock data for testing and development:
- Organizations
- Users (underwriters)
- Underwritings with complete application data
- Purchased processors with configurations
- Underwriting processors (enabled processors per case)
- Documents with revisions
- Mock executions and factors

Usage:
    python scripts/seed_data.py --database postgresql
    python scripts/seed_data.py --database bigquery
    python scripts/seed_data.py --clear  # Clear existing data first
"""

import argparse
import os
import sys
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
import uuid
import random

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Database connection will be added when implementing actual DB operations
# For now, we'll generate the INSERT statements


class DataSeeder:
    """Generates mock data for the AURA underwriting system."""

    def __init__(self, clear_existing=False):
        self.clear_existing = clear_existing
        self.data = {
            "organizations": [],
            "accounts": [],
            "roles": [],
            "underwritings": [],
            "owners": [],
            "owner_addresses": [],
            "merchant_addresses": [],
            "purchased_processors": [],
            "underwriting_processors": [],
            "documents": [],
            "document_revisions": [],
            "processor_executions": [],
            "factors": [],
        }

    def generate_uuid(self):
        """Generate a UUID string."""
        return str(uuid.uuid4())

    def generate_timestamp(self, days_ago=0):
        """Generate a timestamp."""
        return datetime.now(timezone.utc) - timedelta(days=days_ago)

    def seed_all(self):
        """Generate all mock data."""
        print("🌱 Seeding database with mock data...")

        self.seed_organizations()
        self.seed_roles()
        self.seed_accounts()
        self.seed_purchased_processors()
        self.seed_underwritings()
        self.seed_owners()
        self.seed_addresses()
        self.seed_underwriting_processors()
        self.seed_documents()
        self.seed_processor_executions()
        self.seed_factors()

        print("\n✅ Mock data generation complete!")
        self.print_summary()

    def seed_organizations(self):
        """Create mock organizations."""
        print("\n📊 Creating organizations...")

        orgs = [
            {
                "id": self.generate_uuid(),
                "name": "Acme Financial Services",
                "status": "active",
                "created_at": self.generate_timestamp(365),
                "updated_at": self.generate_timestamp(1),
            },
            {
                "id": self.generate_uuid(),
                "name": "TechLend Capital",
                "status": "active",
                "created_at": self.generate_timestamp(180),
                "updated_at": self.generate_timestamp(5),
            },
            {
                "id": self.generate_uuid(),
                "name": "SmallBiz Funding Co",
                "status": "active",
                "created_at": self.generate_timestamp(90),
                "updated_at": self.generate_timestamp(2),
            },
        ]

        self.data["organizations"] = orgs
        print(f"   ✓ Created {len(orgs)} organizations")

    def seed_roles(self):
        """Create system roles."""
        print("\n👤 Creating roles...")

        roles = [
            {
                "id": self.generate_uuid(),
                "name": "MANAGER",
                "description": "Can manage underwritings and users",
                "created_at": self.generate_timestamp(365),
                "updated_at": self.generate_timestamp(365),
            },
            {
                "id": self.generate_uuid(),
                "name": "UNDERWRITER",
                "description": "Can process underwriting applications",
                "created_at": self.generate_timestamp(365),
                "updated_at": self.generate_timestamp(365),
            },
            {
                "id": self.generate_uuid(),
                "name": "VIEWER",
                "description": "Can view underwriting data",
                "created_at": self.generate_timestamp(365),
                "updated_at": self.generate_timestamp(365),
            },
        ]

        self.data["roles"] = roles
        print(f"   ✓ Created {len(roles)} roles")

    def seed_accounts(self):
        """Create mock user accounts."""
        print("\n👥 Creating user accounts...")

        accounts = []
        org = self.data["organizations"][0]  # Use first org

        users = [
            {
                "email": "john.manager@acme.com",
                "first_name": "John",
                "last_name": "Manager",
                "role": "MANAGER",
            },
            {
                "email": "sarah.underwriter@acme.com",
                "first_name": "Sarah",
                "last_name": "Smith",
                "role": "UNDERWRITER",
            },
            {
                "email": "mike.underwriter@acme.com",
                "first_name": "Mike",
                "last_name": "Johnson",
                "role": "UNDERWRITER",
            },
            {
                "email": "lisa.viewer@acme.com",
                "first_name": "Lisa",
                "last_name": "Chen",
                "role": "VIEWER",
            },
        ]

        for user in users:
            account = {
                "id": self.generate_uuid(),
                "organization_id": org["id"],
                "firebase_uid": f"firebase_{self.generate_uuid()[:8]}",
                "email": user["email"],
                "first_name": user["first_name"],
                "last_name": user["last_name"],
                "status": "active",
                "created_at": self.generate_timestamp(90),
                "updated_at": self.generate_timestamp(1),
            }
            accounts.append(account)

        self.data["accounts"] = accounts
        print(f"   ✓ Created {len(accounts)} user accounts")

    def seed_purchased_processors(self):
        """Create purchased processor subscriptions."""
        print("\n🔧 Creating purchased processors...")

        org = self.data["organizations"][0]
        purchaser = self.data["accounts"][0]

        processors = [
            {
                "id": self.generate_uuid(),
                "organization_id": org["id"],
                "processor": "p_bank_statement_analyzer",
                "name": "Bank Statement Analyzer",
                "auto": True,
                "status": "active",
                "config": {
                    "minimum_document": 3,
                    "analysis_window_months": 6,
                    "nsf_threshold_amount": 35.00,
                },
                "price_amount": 500,  # $5.00 in cents
                "price_unit": "execution",
                "price_currency": "USD",
                "purchased_at": self.generate_timestamp(60),
                "purchased_by": purchaser["id"],
            },
            {
                "id": self.generate_uuid(),
                "organization_id": org["id"],
                "processor": "p_credit_check_experian",
                "name": "Experian Business Credit Check",
                "auto": True,
                "status": "active",
                "config": {
                    "include_trade_lines": True,
                    "include_public_records": True,
                    "credit_score_threshold": 600,
                },
                "price_amount": 1500,  # $15.00 in cents
                "price_unit": "execution",
                "price_currency": "USD",
                "purchased_at": self.generate_timestamp(60),
                "purchased_by": purchaser["id"],
            },
            {
                "id": self.generate_uuid(),
                "organization_id": org["id"],
                "processor": "p_identity_verification",
                "name": "Driver's License Verification",
                "auto": True,
                "status": "active",
                "config": {
                    "require_photo": True,
                    "check_expiration": True,
                    "min_age": 18,
                },
                "price_amount": 300,  # $3.00 in cents
                "price_unit": "document",
                "price_currency": "USD",
                "purchased_at": self.generate_timestamp(60),
                "purchased_by": purchaser["id"],
            },
            {
                "id": self.generate_uuid(),
                "organization_id": org["id"],
                "processor": "p_business_verification",
                "name": "Business Registration Verification",
                "auto": True,
                "status": "active",
                "config": {
                    "verify_ein": True,
                    "check_state_registry": True,
                },
                "price_amount": 800,  # $8.00 in cents
                "price_unit": "execution",
                "price_currency": "USD",
                "purchased_at": self.generate_timestamp(60),
                "purchased_by": purchaser["id"],
            },
            {
                "id": self.generate_uuid(),
                "organization_id": org["id"],
                "processor": "p_clear_report",
                "name": "Thomson Reuters CLEAR Report",
                "auto": False,  # Manual only
                "status": "active",
                "config": {
                    "include_background_check": True,
                    "include_business_search": True,
                },
                "price_amount": 2500,  # $25.00 in cents
                "price_unit": "execution",
                "price_currency": "USD",
                "purchased_at": self.generate_timestamp(60),
                "purchased_by": purchaser["id"],
            },
        ]

        self.data["purchased_processors"] = processors
        print(f"   ✓ Created {len(processors)} purchased processors")

    def seed_underwritings(self):
        """Create mock underwriting cases."""
        print("\n📋 Creating underwritings...")

        org = self.data["organizations"][0]
        creator = self.data["accounts"][1]  # Sarah the underwriter

        underwritings = [
            {
                "id": self.generate_uuid(),
                "organization_id": org["id"],
                "serial_number": "A-102224-001",
                "status": "processing",
                "application_type": "NEW",
                "request_amount": 150000.00,
                "request_date": self.generate_timestamp(7).date(),
                "purpose": "Equipment financing and working capital",
                # ISO details
                "iso_ref_id": "iso_12345",
                "iso_name": "Best Funding Partners",
                "iso_email": "contact@bestfunding.com",
                "iso_phone": "555-0100",
                # Representative details
                "representative_ref_id": "rep_001",
                "representative_first_name": "Robert",
                "representative_last_name": "Martinez",
                "representative_email": "robert@techstartup.com",
                "representative_phone_mobile": "555-0101",
                "representative_phone_work": "555-0102",
                # Merchant details
                "merchant_ref_id": "merch_001",
                "merchant_name": "TechStartup Solutions Inc",
                "merchant_dba_name": "TechStartup",
                "merchant_email": "info@techstartup.com",
                "merchant_phone": "555-0103",
                "merchant_website": "https://techstartup.com",
                "merchant_industry": "5734",  # Computer software stores
                "merchant_ein": "12-3456789",
                "merchant_entity_type": "Corporation",
                "merchant_incorporation_date": (datetime.now(timezone.utc) - timedelta(days=1095)).date(),
                "merchant_state_of_incorporation": "CA",
                "created_at": self.generate_timestamp(7),
                "updated_at": self.generate_timestamp(1),
                "created_by": creator["id"],
                "updated_by": creator["id"],
            },
            {
                "id": self.generate_uuid(),
                "organization_id": org["id"],
                "serial_number": "A-102224-002",
                "status": "passed",
                "application_type": "NEW",
                "request_amount": 75000.00,
                "request_date": self.generate_timestamp(14).date(),
                "purpose": "Inventory purchase",
                # ISO details
                "iso_ref_id": "iso_12346",
                "iso_name": "Prime Business Capital",
                "iso_email": "sales@primecapital.com",
                "iso_phone": "555-0200",
                # Representative details
                "representative_ref_id": "rep_002",
                "representative_first_name": "Maria",
                "representative_last_name": "Garcia",
                "representative_email": "maria@retailshop.com",
                "representative_phone_mobile": "555-0201",
                # Merchant details
                "merchant_ref_id": "merch_002",
                "merchant_name": "Downtown Retail Shop LLC",
                "merchant_dba_name": "Downtown Retail",
                "merchant_email": "contact@retailshop.com",
                "merchant_phone": "555-0203",
                "merchant_website": "https://retailshop.com",
                "merchant_industry": "5311",  # Department stores
                "merchant_ein": "98-7654321",
                "merchant_entity_type": "LLC",
                "merchant_incorporation_date": (datetime.now(timezone.utc) - timedelta(days=1825)).date(),
                "merchant_state_of_incorporation": "NY",
                "created_at": self.generate_timestamp(14),
                "updated_at": self.generate_timestamp(2),
                "created_by": creator["id"],
                "updated_by": creator["id"],
            },
            {
                "id": self.generate_uuid(),
                "organization_id": org["id"],
                "serial_number": "A-102224-003",
                "status": "created",
                "application_type": "RENEWAL",
                "request_amount": 200000.00,
                "request_date": self.generate_timestamp(2).date(),
                "purpose": "Business expansion - new location",
                # ISO details
                "iso_ref_id": "iso_12345",
                "iso_name": "Best Funding Partners",
                "iso_email": "contact@bestfunding.com",
                "iso_phone": "555-0100",
                # Representative details
                "representative_ref_id": "rep_003",
                "representative_first_name": "David",
                "representative_last_name": "Kim",
                "representative_email": "david@restaurant.com",
                "representative_phone_mobile": "555-0301",
                # Merchant details
                "merchant_ref_id": "merch_003",
                "merchant_name": "Golden Dragon Restaurant Group Inc",
                "merchant_dba_name": "Golden Dragon",
                "merchant_email": "info@goldendragon.com",
                "merchant_phone": "555-0303",
                "merchant_website": "https://goldendragon.com",
                "merchant_industry": "5812",  # Eating places, restaurants
                "merchant_ein": "45-6789012",
                "merchant_entity_type": "Corporation",
                "merchant_incorporation_date": (datetime.now(timezone.utc) - timedelta(days=2555)).date(),
                "merchant_state_of_incorporation": "TX",
                "created_at": self.generate_timestamp(2),
                "updated_at": self.generate_timestamp(1),
                "created_by": creator["id"],
                "updated_by": creator["id"],
            },
        ]

        self.data["underwritings"] = underwritings
        print(f"   ✓ Created {len(underwritings)} underwritings")
    
    def seed_owners(self):
        """Create mock beneficial owners for underwritings."""
        print("\n👨‍💼 Creating beneficial owners...")
        
        creator = self.data["accounts"][1]
        owners = []
        
        # Owner data for each underwriting
        owners_data = [
            # TechStartup Solutions Inc owners
            [
                {
                    "first_name": "Robert",
                    "last_name": "Martinez",
                    "email": "robert@techstartup.com",
                    "phone_mobile": "555-0101",
                    "phone_work": "555-0102",
                    "birthday": (datetime.now(timezone.utc) - timedelta(days=15330)).date(),  # ~42 years old
                    "fico_score": 720,
                    "ssn": "123-45-6789",
                    "ownership_percent": 60.0,
                    "primary_owner": True,
                },
                {
                    "first_name": "Jennifer",
                    "last_name": "Chen",
                    "email": "jennifer@techstartup.com",
                    "phone_mobile": "555-0104",
                    "birthday": (datetime.now(timezone.utc) - timedelta(days=13140)).date(),  # ~36 years old
                    "fico_score": 695,
                    "ssn": "234-56-7890",
                    "ownership_percent": 40.0,
                    "primary_owner": False,
                },
            ],
            # Downtown Retail Shop LLC owners
            [
                {
                    "first_name": "Maria",
                    "last_name": "Garcia",
                    "email": "maria@retailshop.com",
                    "phone_mobile": "555-0201",
                    "phone_work": "555-0202",
                    "phone_home": "555-0203",
                    "birthday": (datetime.now(timezone.utc) - timedelta(days=18250)).date(),  # ~50 years old
                    "fico_score": 740,
                    "ssn": "345-67-8901",
                    "ownership_percent": 100.0,
                    "primary_owner": True,
                },
            ],
            # Golden Dragon Restaurant Group owners
            [
                {
                    "first_name": "David",
                    "last_name": "Kim",
                    "email": "david@restaurant.com",
                    "phone_mobile": "555-0301",
                    "phone_work": "555-0302",
                    "birthday": (datetime.now(timezone.utc) - timedelta(days=16425)).date(),  # ~45 years old
                    "fico_score": 710,
                    "ssn": "456-78-9012",
                    "ownership_percent": 55.0,
                    "primary_owner": True,
                },
                {
                    "first_name": "Susan",
                    "last_name": "Park",
                    "email": "susan@restaurant.com",
                    "phone_mobile": "555-0304",
                    "birthday": (datetime.now(timezone.utc) - timedelta(days=14235)).date(),  # ~39 years old
                    "fico_score": 685,
                    "ssn": "567-89-0123",
                    "ownership_percent": 45.0,
                    "primary_owner": False,
                },
            ],
        ]
        
        for idx, uw in enumerate(self.data["underwritings"]):
            for owner_data in owners_data[idx]:
                owner = {
                    "id": self.generate_uuid(),
                    "underwriting_id": uw["id"],
                    "first_name": owner_data["first_name"],
                    "last_name": owner_data["last_name"],
                    "email": owner_data["email"],
                    "phone_mobile": owner_data["phone_mobile"],
                    "phone_work": owner_data.get("phone_work"),
                    "phone_home": owner_data.get("phone_home"),
                    "birthday": owner_data["birthday"],
                    "fico_score": owner_data["fico_score"],
                    "ssn": owner_data["ssn"],
                    "enabled": True,
                    "ownership_percent": owner_data["ownership_percent"],
                    "primary_owner": owner_data["primary_owner"],
                    "created_at": uw["created_at"],
                    "created_by": creator["id"],
                    "updated_at": uw["updated_at"],
                    "updated_by": creator["id"],
                }
                owners.append(owner)
        
        self.data["owners"] = owners
        print(f"   ✓ Created {len(owners)} beneficial owners")
    
    def seed_addresses(self):
        """Create addresses for merchants and owners."""
        print("\n🏠 Creating addresses...")
        
        creator = self.data["accounts"][1]
        merchant_addresses = []
        owner_addresses = []
        
        # Merchant addresses
        merchant_addrs = [
            {
                "addr_1": "123 Tech Park Drive",
                "addr_2": "Suite 200",
                "city": "San Francisco",
                "state": "CA",
                "zip": "94105",
            },
            {
                "addr_1": "456 Main Street",
                "addr_2": None,
                "city": "New York",
                "state": "NY",
                "zip": "10001",
            },
            {
                "addr_1": "789 Restaurant Row",
                "addr_2": "Building A",
                "city": "Austin",
                "state": "TX",
                "zip": "78701",
            },
        ]
        
        for idx, uw in enumerate(self.data["underwritings"]):
            addr_data = merchant_addrs[idx]
            addr = {
                "id": self.generate_uuid(),
                "underwriting_id": uw["id"],
                "addr_1": addr_data["addr_1"],
                "addr_2": addr_data["addr_2"],
                "city": addr_data["city"],
                "state": addr_data["state"],
                "zip": addr_data["zip"],
                "created_at": uw["created_at"],
                "created_by": creator["id"],
                "updated_at": uw["updated_at"],
                "updated_by": creator["id"],
            }
            merchant_addresses.append(addr)
        
        # Owner addresses
        owner_addrs = [
            # TechStartup owners
            [
                {
                    "addr_1": "100 Hillside Avenue",
                    "city": "Palo Alto",
                    "state": "CA",
                    "zip": "94301",
                },
                {
                    "addr_1": "250 Oak Street",
                    "addr_2": "Apt 5B",
                    "city": "San Jose",
                    "state": "CA",
                    "zip": "95110",
                },
            ],
            # Retail Shop owner
            [
                {
                    "addr_1": "88 Brooklyn Heights",
                    "city": "Brooklyn",
                    "state": "NY",
                    "zip": "11201",
                },
            ],
            # Restaurant owners
            [
                {
                    "addr_1": "500 Lakeside Drive",
                    "city": "Austin",
                    "state": "TX",
                    "zip": "78703",
                },
                {
                    "addr_1": "600 Garden Way",
                    "city": "Austin",
                    "state": "TX",
                    "zip": "78704",
                },
            ],
        ]
        
        owner_idx = 0
        for uw_idx, uw in enumerate(self.data["underwritings"]):
            uw_owners = [o for o in self.data["owners"] if o["underwriting_id"] == uw["id"]]
            for addr_idx, owner in enumerate(uw_owners):
                addr_data = owner_addrs[uw_idx][addr_idx]
                addr = {
                    "id": self.generate_uuid(),
                    "owner_id": owner["id"],
                    "addr_1": addr_data["addr_1"],
                    "addr_2": addr_data.get("addr_2"),
                    "city": addr_data["city"],
                    "state": addr_data["state"],
                    "zip": addr_data["zip"],
                    "created_at": owner["created_at"],
                    "created_by": creator["id"],
                    "updated_at": owner["updated_at"],
                    "updated_by": creator["id"],
                }
                owner_addresses.append(addr)
        
        self.data["merchant_addresses"] = merchant_addresses
        self.data["owner_addresses"] = owner_addresses
        print(f"   ✓ Created {len(merchant_addresses)} merchant addresses and {len(owner_addresses)} owner addresses")

    def seed_underwriting_processors(self):
        """Create underwriting processor configurations."""
        print("\n⚙️  Creating underwriting processor configurations...")

        creator = self.data["accounts"][1]
        configs = []

        # For each underwriting, enable purchased processors
        for uw in self.data["underwritings"]:
            for pp in self.data["purchased_processors"][:4]:  # Enable first 4 processors
                config = {
                    "id": self.generate_uuid(),
                    "organization_id": uw["organization_id"],
                    "underwriting_id": uw["id"],
                    "purchased_processor_id": pp["id"],
                    "processor": pp["processor"],
                    "name": pp["name"],
                    "auto": pp["auto"],
                    "enabled": True,
                    "config_override": {},  # No overrides for this seed
                    "effective_config": pp["config"],
                    "current_executions_list": [],
                    "created_at": uw["created_at"],
                    "created_by": creator["id"],
                    "updated_at": uw["updated_at"],
                    "updated_by": creator["id"],
                }
                configs.append(config)

        self.data["underwriting_processors"] = configs
        print(f"   ✓ Created {len(configs)} underwriting processor configs")

    def seed_documents(self):
        """Create mock documents with revisions."""
        print("\n📄 Creating documents...")

        creator = self.data["accounts"][1]
        documents = []
        revisions = []

        # Document types
        doc_types = [
            ("s_bank_statement", "Bank Statement"),
            ("s_drivers_license", "Driver's License"),
            ("s_voided_check", "Voided Check"),
            ("s_tax_return", "Tax Return"),
        ]

        for uw in self.data["underwritings"][:2]:  # First 2 underwritings
            for doc_type, doc_name in doc_types:
                doc_id = self.generate_uuid()
                rev_id = self.generate_uuid()

                # Create document
                doc = {
                    "id": doc_id,
                    "organization_id": uw["organization_id"],
                    "underwriting_id": uw["id"],
                    "status": "accepted",
                    "current_revision_id": rev_id,
                    "stipulation_type": doc_type,
                    "classification_confidence": 0.95,
                    "created_at": uw["created_at"],
                    "created_by": creator["id"],
                    "updated_at": uw["updated_at"],
                    "updated_by": creator["id"],
                }
                documents.append(doc)

                # Create revision
                revision = {
                    "id": rev_id,
                    "document_id": doc_id,
                    "gcs_uri": f"gs://aura-documents/{uw['id']}/{doc_type}_{rev_id}.pdf",
                    "ocr_gcs_uri": f"gs://aura-documents/{uw['id']}/{doc_type}_{rev_id}_ocr.json",
                    "filename": f"{doc_name.replace(' ', '_')}_{datetime.now(timezone.utc).strftime('%Y%m%d')}.pdf",
                    "mime_type": "application/pdf",
                    "size_bytes": random.randint(100000, 5000000),
                    "quality_score": 0.92,
                    "page_count": random.randint(1, 8),
                    "created_at": uw["created_at"],
                    "created_by": creator["id"],
                    "updated_at": uw["updated_at"],
                    "updated_by": creator["id"],
                }
                revisions.append(revision)

        self.data["documents"] = documents
        self.data["document_revisions"] = revisions
        print(f"   ✓ Created {len(documents)} documents with {len(revisions)} revisions")

    def seed_processor_executions(self):
        """Create mock processor executions."""
        print("\n🔄 Creating processor executions...")

        executions = []

        # Create executions for first underwriting
        uw = self.data["underwritings"][0]
        uw_processors = [up for up in self.data["underwriting_processors"]
                        if up["underwriting_id"] == uw["id"]]

        for up in uw_processors[:2]:  # First 2 processors
            exec_id = self.generate_uuid()

            execution = {
                "id": exec_id,
                "organization_id": up["organization_id"],
                "underwriting_id": up["underwriting_id"],
                "underwriting_processor_id": up["id"],
                "processor": up["processor"],
                "status": "completed",
                "enabled": True,
                "payload": {
                    "underwriting_id": uw["id"],
                    "documents": ["doc_1", "doc_2", "doc_3"],
                },
                "payload_hash": f"hash_{self.generate_uuid()[:16]}",
                "output": {
                    "monthly_revenues": [45000.0, 48000.0, 46500.0],
                    "avg_monthly_revenue": 46500.0,
                    "months_analyzed": 3,
                },
                "factors_delta": {
                    "f_avg_monthly_revenue": 46500.0,
                    "f_months_analyzed": 3,
                },
                "document_revision_ids": [],
                "run_cost_cents": 500,
                "currency": "USD",
                "started_at": self.generate_timestamp(5),
                "completed_at": self.generate_timestamp(5),
                "created_at": self.generate_timestamp(5),
                "created_by": None,
                "updated_at": self.generate_timestamp(5),
                "updated_by": None,
            }
            executions.append(execution)

            # Update current_executions_list
            up["current_executions_list"].append(exec_id)

        self.data["processor_executions"] = executions
        print(f"   ✓ Created {len(executions)} processor executions")

    def seed_factors(self):
        """Create mock factors."""
        print("\n📊 Creating factors...")

        factors = []

        # Create factors for first underwriting
        uw = self.data["underwritings"][0]
        executions = [e for e in self.data["processor_executions"]
                     if e["underwriting_id"] == uw["id"]]

        for execution in executions:
            for factor_key, value in execution["factors_delta"].items():
                factor = {
                    "id": self.generate_uuid(),
                    "organization_id": execution["organization_id"],
                    "underwriting_id": execution["underwriting_id"],
                    "factor_key": factor_key,
                    "value": value,
                    "unit": "USD" if "revenue" in factor_key else None,
                    "source": "processor",
                    "status": "active",
                    "underwriting_processor_id": execution["underwriting_processor_id"],
                    "execution_id": execution["id"],
                    "created_at": execution["completed_at"],
                    "created_by": None,
                    "updated_at": execution["completed_at"],
                    "updated_by": None,
                }
                factors.append(factor)

        self.data["factors"] = factors
        print(f"   ✓ Created {len(factors)} factors")

    def print_summary(self):
        """Print summary of generated data."""
        print("\n" + "="*70)
        print("📊 SEED DATA SUMMARY")
        print("="*70)

        for key, items in self.data.items():
            if items:
                print(f"{key.replace('_', ' ').title()}: {len(items)}")

        print("\n" + "="*70)
        print("\n📝 SAMPLE DATA:")
        print("="*70)

        if self.data["organizations"]:
            org = self.data["organizations"][0]
            print(f"\n🏢 Organization: {org['name']}")
            print(f"   ID: {org['id']}")

        if self.data["accounts"]:
            print(f"\n👥 Users:")
            for acc in self.data["accounts"][:3]:
                print(f"   • {acc['first_name']} {acc['last_name']} ({acc['email']})")

        if self.data["purchased_processors"]:
            print(f"\n🔧 Purchased Processors:")
            for pp in self.data["purchased_processors"][:3]:
                print(f"   • {pp['name']} (${pp['price_amount']/100:.2f} per {pp['price_unit']})")

        if self.data["underwritings"]:
            print(f"\n📋 Underwritings:")
            for uw in self.data["underwritings"]:
                print(f"   • {uw['serial_number']} - {uw['merchant_name']} (${uw['request_amount']:,.2f}) [{uw['status']}]")
        
        if self.data["owners"]:
            print(f"\n👨‍💼 Beneficial Owners:")
            for owner in self.data["owners"][:5]:
                primary = "PRIMARY" if owner["primary_owner"] else "CO-OWNER"
                print(f"   • {owner['first_name']} {owner['last_name']} - {owner['ownership_percent']}% ({primary}) FICO: {owner['fico_score']}")
        
        print("\n" + "="*70)

    def export_sql(self, database_type="postgresql"):
        """Export data as SQL INSERT statements."""
        print(f"\n📝 Generating {database_type.upper()} SQL statements...")

        output_file = Path(__file__).parent / f"seed_data_{database_type}.sql"

        with open(output_file, "w") as f:
            f.write(f"-- AURA Underwriting System Seed Data\n")
            f.write(f"-- Generated: {datetime.now(timezone.utc).isoformat()}\n")
            f.write(f"-- Database: {database_type}\n\n")

            if self.clear_existing:
                f.write("-- Clear existing data\n")
                f.write("TRUNCATE TABLE factors CASCADE;\n")
                f.write("TRUNCATE TABLE processor_executions CASCADE;\n")
                f.write("TRUNCATE TABLE document_revisions CASCADE;\n")
                f.write("TRUNCATE TABLE documents CASCADE;\n")
                f.write("TRUNCATE TABLE underwriting_processors CASCADE;\n")
                f.write("TRUNCATE TABLE purchased_processors CASCADE;\n")
                f.write("TRUNCATE TABLE underwritings CASCADE;\n")
                f.write("TRUNCATE TABLE accounts CASCADE;\n")
                f.write("TRUNCATE TABLE roles CASCADE;\n")
                f.write("TRUNCATE TABLE organizations CASCADE;\n\n")

            # Generate INSERT statements for each table
            # (Simplified - actual implementation would generate proper SQL)
            f.write("-- Insert Organizations\n")
            for org in self.data["organizations"]:
                f.write(f"-- INSERT INTO organizations VALUES ({org['id']}, '{org['name']}', ...);\n")

            f.write("\n-- Insert Roles\n")
            for role in self.data["roles"]:
                f.write(f"-- INSERT INTO roles VALUES ({role['id']}, '{role['name']}', ...);\n")

            f.write("\n-- Insert Accounts\n")
            for acc in self.data["accounts"]:
                f.write(f"-- INSERT INTO accounts VALUES ({acc['id']}, '{acc['email']}', ...);\n")

            f.write("\n-- More INSERT statements would follow...\n")

        print(f"   ✓ SQL file generated: {output_file}")
        return output_file

    def export_json(self):
        """Export data as JSON file."""
        print(f"\n📝 Generating JSON export...")

        output_file = Path(__file__).parent / "seed_data.json"

        # Convert datetime objects to ISO format strings
        def serialize_datetime(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            elif isinstance(obj, (list, dict)):
                return obj
            return str(obj)

        json_data = {}
        for key, items in self.data.items():
            json_data[key] = []
            for item in items:
                serialized_item = {}
                for k, v in item.items():
                    serialized_item[k] = serialize_datetime(v)
                json_data[key].append(serialized_item)

        with open(output_file, "w") as f:
            json.dump(json_data, f, indent=2, default=str)

        print(f"   ✓ JSON file generated: {output_file}")
        return output_file


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Seed AURA database with mock data")
    parser.add_argument(
        "--database",
        choices=["postgresql", "bigquery"],
        default="postgresql",
        help="Database type to generate SQL for"
    )
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Clear existing data before seeding"
    )
    parser.add_argument(
        "--export-sql",
        action="store_true",
        help="Export as SQL file instead of direct insertion"
    )
    parser.add_argument(
        "--export-json",
        action="store_true",
        help="Export as JSON file for easy data access"
    )

    args = parser.parse_args()

    print("╔═══════════════════════════════════════════════════════════════════════╗")
    print("║                                                                       ║")
    print("║   🌱 AURA Database Seeder 🌱                                         ║")
    print("║                                                                       ║")
    print("╚═══════════════════════════════════════════════════════════════════════╝")

    seeder = DataSeeder(clear_existing=args.clear)
    seeder.seed_all()

    if args.export_sql:
        seeder.export_sql(args.database)

    if args.export_json:
        seeder.export_json()

    print("\n✨ Seeding complete! Ready for testing.\n")


if __name__ == "__main__":
    main()

