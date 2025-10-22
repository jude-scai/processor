# Database Scripts

This directory contains migration and seeding scripts for PostgreSQL and BigQuery databases.

## Table of Contents

1. [Database Seeder](#database-seeder) - Generate mock data for testing
2. [PostgreSQL Migration](#postgresql-migration) - PostgreSQL schema setup
3. [BigQuery Migration](#bigquery-migration) - BigQuery schema setup

---

## Database Seeder (`seed_data.py`)

Generates comprehensive mock data for the AURA underwriting system, including organizations, users, underwritings, purchased processors, documents, executions, and factors.

### Quick Start

```bash
# Generate mock data and display summary
python scripts/seed_data.py

# Export as JSON for easy access
python scripts/seed_data.py --export-json

# Export as SQL for PostgreSQL
python scripts/seed_data.py --export-sql --database postgresql

# Clear existing data before seeding
python scripts/seed_data.py --clear
```

### Features

- ✅ **Complete Mock Data**: Organizations, users, underwritings, processors, documents, executions, factors
- ✅ **Realistic Data**: Valid UUIDs, timestamps, business data, processor configurations
- ✅ **Multiple Export Formats**: JSON and SQL export options
- ✅ **Flexible**: Support for both PostgreSQL and BigQuery
- ✅ **Summary Output**: Clear overview of generated data

### Generated Data

| Entity | Count | Description |
|--------|-------|-------------|
| Organizations | 3 | Acme Financial Services, TechLend Capital, SmallBiz Funding Co |
| Accounts | 4 | Manager, 2 Underwriters, Viewer |
| Roles | 3 | MANAGER, UNDERWRITER, VIEWER |
| Underwritings | 3 | TechStartup ($150k), Retail Shop ($75k), Restaurant ($200k) |
| Purchased Processors | 5 | Bank Statement, Credit Check, Identity, Business Verification, CLEAR |
| Underwriting Processors | 12 | 4 processors × 3 underwritings |
| Documents | 8 | Bank statements, driver's licenses, voided checks, tax returns |
| Document Revisions | 8 | One revision per document |
| Processor Executions | 2 | Completed executions with outputs |
| Factors | 4 | Extracted factors from executions |

### Purchased Processors Details

1. **Bank Statement Analyzer**
   - Cost: $5.00 per execution
   - Config: `minimum_document: 3`, `analysis_window_months: 6`, `nsf_threshold_amount: 35.00`
   - Auto-execution: Enabled

2. **Experian Business Credit Check**
   - Cost: $15.00 per execution
   - Config: `include_trade_lines: true`, `credit_score_threshold: 600`
   - Auto-execution: Enabled

3. **Driver's License Verification**
   - Cost: $3.00 per document
   - Config: `require_photo: true`, `check_expiration: true`, `min_age: 18`
   - Auto-execution: Enabled

4. **Business Registration Verification**
   - Cost: $8.00 per execution
   - Config: `verify_ein: true`, `check_state_registry: true`
   - Auto-execution: Enabled

5. **Thomson Reuters CLEAR Report**
   - Cost: $25.00 per execution
   - Config: `include_background_check: true`, `include_business_search: true`
   - Auto-execution: Disabled (manual only)

### Command-Line Options

```bash
python scripts/seed_data.py [OPTIONS]

Options:
  --database {postgresql,bigquery}  Database type (default: postgresql)
  --clear                            Clear existing data before seeding
  --export-sql                       Export as SQL file
  --export-json                      Export as JSON file
  -h, --help                         Show help message
```

### Example Output

```
╔═══════════════════════════════════════════════════════════════════════╗
║                                                                       ║
║   🌱 AURA Database Seeder 🌱                                         ║
║                                                                       ║
╚═══════════════════════════════════════════════════════════════════════╝
🌱 Seeding database with mock data...

📊 Creating organizations...
   ✓ Created 3 organizations

👥 Creating user accounts...
   ✓ Created 4 user accounts

🔧 Creating purchased processors...
   ✓ Created 5 purchased processors

📋 Creating underwritings...
   ✓ Created 3 underwritings

✅ Mock data generation complete!

📋 Underwritings:
   • A-102224-001 - TechStartup Solutions Inc ($150,000.00) [processing]
   • A-102224-002 - Downtown Retail Shop LLC ($75,000.00) [passed]
   • A-102224-003 - Golden Dragon Restaurant Group Inc ($200,000.00) [created]
```

### JSON Export Structure

The JSON export (`seed_data.json`) contains all entities with proper serialization:

```json
{
  "organizations": [...],
  "accounts": [...],
  "roles": [...],
  "underwritings": [...],
  "purchased_processors": [...],
  "underwriting_processors": [...],
  "documents": [...],
  "document_revisions": [...],
  "processor_executions": [...],
  "factors": [...]
}
```

### Use Cases

1. **Testing**: Load mock data for integration tests
2. **Development**: Populate local database for UI development
3. **Demos**: Create realistic data for demonstrations
4. **CI/CD**: Seed test databases in pipelines

---

## PostgreSQL Migration (`postgresql-init/migrate.py`)

### Quick Start

```bash
# Run migration with defaults from .env
python scripts/postgresql-init/migrate.py

# Drop existing tables and recreate (DESTRUCTIVE)
python scripts/postgresql-init/migrate.py --drop
```

### Features

- ✅ **Automatic Wait**: Waits up to 60 seconds for PostgreSQL to be ready
- ✅ **Database Creation**: Creates database if it doesn't exist
- ✅ **Full Schema**: Creates all 25 tables from schema.sql
- ✅ **Seed Data**: Loads initial data (organization, roles, permissions)
- ✅ **Verification**: Verifies all critical tables exist after migration
- ✅ **Progress Output**: Detailed progress and status messages
- ✅ **Idempotent**: Safe to run multiple times (without --drop)

### Command-Line Options

```bash
python scripts/postgresql-init/migrate.py [OPTIONS]

Options:
  --host HOST               PostgreSQL host (default: from .env)
  --port PORT               PostgreSQL port (default: from .env)
  --database, --db DB       Database name (default: from .env)
  --user USER               Database user (default: from .env)
  --password PASSWORD       Database password (default: from .env)
  --drop                    Drop existing tables before migration (DESTRUCTIVE)
  --no-wait                 Don't wait for PostgreSQL to be ready
  -h, --help                Show help message
```

### Example Output

```
======================================================================
🐘 AURA PostgreSQL Database Migration
======================================================================
Host:     localhost:5432
Database: aura_underwriting
User:     aura_user
======================================================================

⏳ Waiting for PostgreSQL at localhost:5432...
✅ PostgreSQL is ready (attempt 1/30)

📦 Creating database 'aura_underwriting'...
✅ Database 'aura_underwriting' created

📖 Reading schema from: /path/to/schema.sql
✅ Schema file loaded (20984 bytes)

🚀 Starting migration to 'aura_underwriting'...
📝 Executing schema SQL...
✅ Migration completed successfully!
📊 Total tables created: 25

📋 Tables created:
    1. account
    2. account_role
    3. decision
    ...
   25. underwriting_score

🔍 Verifying migration...
✅ All 12 critical tables verified
✅ Seed data loaded: 1 organizations, 4 roles

======================================================================
✅ Migration completed successfully!
======================================================================

🎉 Database is ready for use!

Connection string:
postgresql://aura_user:****@localhost:5432/aura_underwriting
```

### Schema File

The migration reads from `postgresql-init/schema.sql` which contains:

- **25 Tables**: All AURA underwriting system tables
- **Constraints**: Foreign keys, unique constraints, check constraints
- **Indexes**: Performance optimization indexes
- **Seed Data**: Initial organizations, roles, and permissions

### Use Cases

#### 1. Initial Setup
```bash
# First time setup
docker compose up -d
python scripts/postgresql-init/migrate.py
```

#### 2. Reset Database (Development)
```bash
# Drop and recreate everything
python scripts/postgresql-init/migrate.py --drop
```

#### 3. Custom Database
```bash
# Migrate to different database
python scripts/postgresql-init/migrate.py \
  --host production.db.internal \
  --port 5432 \
  --db aura_prod \
  --user admin \
  --password $DB_PASSWORD
```

#### 4. CI/CD Pipeline
```bash
# Non-interactive migration for CI/CD
python scripts/postgresql-init/migrate.py --no-wait
```

---

## BigQuery Migration (`bigquery-init/migrate.py`)

### Quick Start

```bash
# Requires BigQuery emulator running
docker compose --profile bigquery up -d

# Run migration
python scripts/bigquery-init/migrate.py
```

### Features

- ✅ Dataset creation (underwriting_data)
- ✅ Table creation from schema definitions
- ⚠️ **Note**: BigQuery emulator has limited functionality and performance issues

### Use Cases

The BigQuery migration is primarily for:
- Testing BigQuery-specific features
- Validating BigQuery compatibility
- Prototyping production BigQuery schema

**Recommendation**: Use PostgreSQL for local development. The BigQuery emulator is experimental and has known limitations.

---

## Schema Files

### PostgreSQL Schema (`postgresql-init/schema.sql`)
- Full SQL with CREATE TABLE statements
- Complete constraints and indexes
- Seed data included
- Auto-loaded by Docker on container creation
- Used by migrate.py for programmatic migration

### BigQuery Schema (`bigquery-init/schema.sql`)
- BigQuery-compatible DDL syntax
- Modified data types for BigQuery
- Used by BigQuery migrate.py

---

## Environment Configuration

Both migration scripts read from `.env` file:

```env
# PostgreSQL
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=aura_underwriting
POSTGRES_USER=aura_user
POSTGRES_PASSWORD=aura_password

# BigQuery
BIGQUERY_PROJECT=aura-project
BIGQUERY_DATASET=underwriting_data
BIGQUERY_EMULATOR_HOST=localhost:9050
```

---

## Troubleshooting

### PostgreSQL Connection Refused
```bash
# Check PostgreSQL is running
docker compose ps postgres

# Check logs
docker compose logs postgres

# Wait longer for startup
python scripts/postgresql-init/migrate.py  # Already has 60s timeout
```

### Tables Already Exist
```bash
# Use --drop to recreate
python scripts/postgresql-init/migrate.py --drop

# Or manually drop database
docker compose exec postgres psql -U aura_user -d postgres -c "DROP DATABASE aura_underwriting;"
```

### Permission Denied
```bash
# Ensure user has CREATE DATABASE permission
# Check .env credentials match docker-compose.yml
```

### Schema File Not Found
```bash
# Verify file exists
ls -la scripts/postgresql-init/schema.sql

# Run from project root directory
cd /path/to/processor
python scripts/postgresql-init/migrate.py
```

---

## Development Workflow

### Recommended Development Flow

1. **Start Services**
   ```bash
   docker compose up -d
   ```

2. **Schema Auto-Loaded** (by Docker init)
   - PostgreSQL automatically loads `schema.sql` on first start
   - No migration needed for fresh containers

3. **Manual Migration** (optional)
   ```bash
   # Only needed if you want to recreate schema
   python scripts/postgresql-init/migrate.py --drop
   ```

4. **Run Tests**
   ```bash
   pytest tests/integration/test_services.py -v
   ```

### Schema Changes Workflow

When you modify `schema.sql`:

1. **Drop and recreate** (development)
   ```bash
   python scripts/postgresql-init/migrate.py --drop
   ```

2. **Or recreate container** (clean slate)
   ```bash
   docker compose down -v
   docker compose up -d
   ```

3. **Verify changes**
   ```bash
   pytest tests/integration/test_services.py::TestPostgreSQL -v
   ```

---

## Summary

| Script | Status | Speed | Recommended For |
|--------|--------|-------|-----------------|
| **postgresql-init/migrate.py** | ✅ Working | Fast (<1s) | Local development, testing, CI/CD |
| **bigquery-init/migrate.py** | ⚠️ Limited | Slow (>30s) | BigQuery compatibility testing only |

**Recommendation**: Use PostgreSQL migration script for all local development and testing. It's fast, reliable, and has complete SQL support.

