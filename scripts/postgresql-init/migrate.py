#!/usr/bin/env python3
"""
PostgreSQL Database Migration Script

This script creates all tables and seed data for the AURA underwriting system.
It reads from schema.sql and executes it against the PostgreSQL database.

Usage:
    python scripts/postgresql-init/migrate.py

    Or with custom connection:
    python scripts/postgresql-init/migrate.py --host localhost --port 5432 --db aura_underwriting
"""

import os
import sys
import argparse
import time
from pathlib import Path
from typing import Optional

try:
    import psycopg2
    from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
    from dotenv import load_dotenv
except ImportError as e:
    print(f"❌ Missing required package: {e}")
    print("Install with: pip install psycopg2-binary python-dotenv")
    sys.exit(1)


def load_env_config() -> dict:
    """Load configuration from .env file"""
    load_dotenv()

    return {
        "host": os.getenv("POSTGRES_HOST", "localhost"),
        "port": int(os.getenv("POSTGRES_PORT", "5432")),
        "database": os.getenv("POSTGRES_DB", "aura_underwriting"),
        "user": os.getenv("POSTGRES_USER", "aura_user"),
        "password": os.getenv("POSTGRES_PASSWORD", "aura_password"),
    }


def wait_for_postgres(config: dict, max_retries: int = 30, delay: int = 2) -> bool:
    """Wait for PostgreSQL to be ready"""
    print(f"⏳ Waiting for PostgreSQL at {config['host']}:{config['port']}...")

    for attempt in range(1, max_retries + 1):
        try:
            conn = psycopg2.connect(
                host=config["host"],
                port=config["port"],
                user=config["user"],
                password=config["password"],
                database="postgres",  # Connect to default database first
                connect_timeout=3
            )
            conn.close()
            print(f"✅ PostgreSQL is ready (attempt {attempt}/{max_retries})")
            return True
        except psycopg2.OperationalError as e:
            if attempt < max_retries:
                print(f"   Attempt {attempt}/{max_retries} - waiting {delay}s...")
                time.sleep(delay)
            else:
                print(f"❌ PostgreSQL not ready after {max_retries} attempts")
                print(f"   Error: {e}")
                return False

    return False


def create_database_if_not_exists(config: dict) -> bool:
    """Create database if it doesn't exist"""
    try:
        # Connect to postgres database to create target database
        conn = psycopg2.connect(
            host=config["host"],
            port=config["port"],
            user=config["user"],
            password=config["password"],
            database="postgres"
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()

        # Check if database exists
        cursor.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s",
            (config["database"],)
        )
        exists = cursor.fetchone()

        if not exists:
            print(f"📦 Creating database '{config['database']}'...")
            cursor.execute(f'CREATE DATABASE "{config["database"]}"')
            print(f"✅ Database '{config['database']}' created")
        else:
            print(f"ℹ️  Database '{config['database']}' already exists")

        cursor.close()
        conn.close()
        return True

    except Exception as e:
        print(f"❌ Error creating database: {e}")
        return False


def read_schema_file() -> Optional[str]:
    """Read the schema.sql file"""
    script_dir = Path(__file__).parent
    schema_path = script_dir / "schema.sql"

    if not schema_path.exists():
        print(f"❌ Schema file not found: {schema_path}")
        return None

    print(f"📖 Reading schema from: {schema_path}")

    try:
        with open(schema_path, 'r', encoding='utf-8') as f:
            content = f.read()
        print(f"✅ Schema file loaded ({len(content)} bytes)")
        return content
    except Exception as e:
        print(f"❌ Error reading schema file: {e}")
        return None


def execute_migration(config: dict, schema_sql: str, drop_existing: bool = False) -> bool:
    """Execute the migration SQL"""
    try:
        # Connect to target database
        conn = psycopg2.connect(
            host=config["host"],
            port=config["port"],
            database=config["database"],
            user=config["user"],
            password=config["password"]
        )
        cursor = conn.cursor()

        print(f"\n🚀 Starting migration to '{config['database']}'...")

        # Optionally drop existing tables
        if drop_existing:
            print("⚠️  Dropping existing tables...")
            cursor.execute("""
                DO $$ DECLARE
                    r RECORD;
                BEGIN
                    FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = 'public') LOOP
                        EXECUTE 'DROP TABLE IF EXISTS ' || quote_ident(r.tablename) || ' CASCADE';
                    END LOOP;
                END $$;
            """)
            conn.commit()
            print("✅ Existing tables dropped")

        # Execute the schema SQL
        print("📝 Executing schema SQL...")
        cursor.execute(schema_sql)
        conn.commit()

        # Count created tables
        cursor.execute("""
            SELECT COUNT(*) FROM information_schema.tables
            WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
        """)
        table_count = cursor.fetchone()[0]

        print(f"✅ Migration completed successfully!")
        print(f"📊 Total tables created: {table_count}")

        # List all tables
        cursor.execute("""
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
            ORDER BY table_name
        """)
        tables = [row[0] for row in cursor.fetchall()]

        print("\n📋 Tables created:")
        for i, table in enumerate(tables, 1):
            print(f"   {i:2d}. {table}")

        cursor.close()
        conn.close()
        return True

    except psycopg2.Error as e:
        print(f"❌ Migration failed!")
        print(f"   Error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


def verify_migration(config: dict) -> bool:
    """Verify that migration was successful"""
    try:
        conn = psycopg2.connect(
            host=config["host"],
            port=config["port"],
            database=config["database"],
            user=config["user"],
            password=config["password"]
        )
        cursor = conn.cursor()

        print("\n🔍 Verifying migration...")

        # Check critical tables exist
        critical_tables = [
            'organization', 'account', 'role', 'permission',
            'underwriting', 'document', 'document_revision',
            'organization_processors', 'underwriting_processors', 'processor_executions',
            'factor', 'factor_snapshot'
        ]

        missing_tables = []
        for table in critical_tables:
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = %s
                )
            """, (table,))
            exists = cursor.fetchone()[0]
            if not exists:
                missing_tables.append(table)

        if missing_tables:
            print(f"❌ Missing critical tables: {', '.join(missing_tables)}")
            cursor.close()
            conn.close()
            return False

        print(f"✅ All {len(critical_tables)} critical tables verified")

        # Check for seed data
        cursor.execute("SELECT COUNT(*) FROM organization")
        org_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM role")
        role_count = cursor.fetchone()[0]

        if org_count > 0 or role_count > 0:
            print(f"✅ Seed data loaded: {org_count} organizations, {role_count} roles")
        else:
            print("ℹ️  No seed data found (optional)")

        cursor.close()
        conn.close()
        return True

    except Exception as e:
        print(f"❌ Verification failed: {e}")
        return False


def main():
    """Main migration function"""
    parser = argparse.ArgumentParser(description="PostgreSQL Database Migration Script")
    parser.add_argument("--host", help="PostgreSQL host (default: from .env)")
    parser.add_argument("--port", type=int, help="PostgreSQL port (default: from .env)")
    parser.add_argument("--database", "--db", help="Database name (default: from .env)")
    parser.add_argument("--user", help="Database user (default: from .env)")
    parser.add_argument("--password", help="Database password (default: from .env)")
    parser.add_argument("--drop", action="store_true", help="Drop existing tables before migration")
    parser.add_argument("--no-wait", action="store_true", help="Don't wait for PostgreSQL to be ready")

    args = parser.parse_args()

    # Load configuration
    config = load_env_config()

    # Override with command-line arguments
    if args.host:
        config["host"] = args.host
    if args.port:
        config["port"] = args.port
    if args.database:
        config["database"] = args.database
    if args.user:
        config["user"] = args.user
    if args.password:
        config["password"] = args.password

    print("=" * 70)
    print("🐘 AURA PostgreSQL Database Migration")
    print("=" * 70)
    print(f"Host:     {config['host']}:{config['port']}")
    print(f"Database: {config['database']}")
    print(f"User:     {config['user']}")
    print("=" * 70)
    print()

    # Wait for PostgreSQL to be ready
    if not args.no_wait:
        if not wait_for_postgres(config):
            print("\n❌ Migration aborted: PostgreSQL not ready")
            sys.exit(1)
        print()

    # Create database if needed
    if not create_database_if_not_exists(config):
        print("\n❌ Migration aborted: Could not create database")
        sys.exit(1)
    print()

    # Read schema file
    schema_sql = read_schema_file()
    if not schema_sql:
        print("\n❌ Migration aborted: Could not read schema file")
        sys.exit(1)
    print()

    # Execute migration
    if not execute_migration(config, schema_sql, drop_existing=args.drop):
        print("\n❌ Migration failed!")
        sys.exit(1)

    # Verify migration
    if not verify_migration(config):
        print("\n⚠️  Migration completed but verification failed")
        sys.exit(1)

    print("\n" + "=" * 70)
    print("✅ Migration completed successfully!")
    print("=" * 70)
    print("\n🎉 Database is ready for use!")
    print(f"\nConnection string:")
    print(f"postgresql://{config['user']}:****@{config['host']}:{config['port']}/{config['database']}")
    print()


if __name__ == "__main__":
    main()

