# Processing Engine Repositories

This directory contains the repository layer for the Processing Engine, providing data access abstractions for all database operations needed by processors and the orchestration system.

## Overview

The repository pattern separates data access logic from business logic, making the codebase more maintainable, testable, and flexible. All database operations flow through these repositories, which can be easily mocked for testing or swapped for different database implementations.

## Architecture

```
BaseProcessor (uses) → Repositories (abstract) → Database
                                                   ├─ PostgreSQL
                                                   └─ BigQuery
```

## Repository Components

### 1. ProcessorRepository

**Purpose**: Manages processor configurations and subscriptions at system, tenant, and underwriting levels.

**Key Responsibilities**:
- Fetch processor catalog (code-managed processors)
- Get tenant processor subscriptions (purchased_processors table)
- Retrieve underwriting processor configurations (underwriting_processors table)
- Resolve effective configurations (merging defaults + tenant + underwriting overrides)
- Manage current execution lists per processor

**Core Methods**:

```python
# System-level
get_processor_catalog() -> list[dict]

# Tenant-level (purchased_processors)
get_purchased_processor_by_id(id) -> dict | None
get_purchased_processors_by_organization(org_id, enabled_only, auto_only) -> list[dict]
get_processor_by_name(processor_name, org_id) -> dict | None

# Underwriting-level (underwriting_processors)
get_underwriting_processor_by_id(id) -> dict | None
get_underwriting_processors(underwriting_id, enabled_only, auto_only) -> list[dict]
update_current_executions_list(up_id, execution_ids) -> bool

# Configuration resolution
get_effective_config(up_id) -> dict
```

**Configuration Resolution Flow**:

1. **System Default**: Processor's `CONFIG` class constant (from code)
2. **Tenant Override**: `purchased_processors.config` (tenant-specific settings)
3. **Underwriting Override**: `underwriting_processors.config_override` (case-specific settings)

Result: `effective_config` = System + Tenant + Underwriting (with right-side precedence)

### 2. ExecutionRepository

**Purpose**: Manages processor execution records, status tracking, and supersession relationships.

**Key Responsibilities**:
- Create new execution records
- Track execution status (pending → running → completed/failed)
- Store execution outputs and factor deltas
- Manage supersession chains (updated_execution_id)
- Handle activation/deactivation of executions
- Provide execution history and audit trails

**Core Methods**:

```python
# Creation
create_execution(uw_id, up_id, org_id, processor, payload, hash, ...) -> str
find_execution_by_hash(up_id, hash) -> dict | None

# Status updates
update_execution_status(exec_id, status, started_at, completed_at, ...) -> bool
save_execution_result(exec_id, output, factors, cost, completed_at) -> bool

# Retrieval
get_execution_by_id(exec_id) -> dict | None
get_active_executions(up_id) -> list[dict]
get_executions_by_underwriting(uw_id, processor, status) -> list[dict]

# Supersession
mark_execution_superseded(old_id, new_id) -> bool
get_execution_chain(exec_id) -> list[dict]

# Activation/Deactivation
activate_execution(exec_id) -> bool
deactivate_execution(exec_id) -> bool

# Helpers
get_execution_count(uw_id, processor) -> int
```

**Execution Lifecycle Flow**:

```
1. Create (pending)
   ↓
2. Update to running
   ↓
3. Execute processor logic
   ↓
4. Save result (completed) OR Update to failed
   ↓
5. Optionally supersede previous execution
   ↓
6. Activate/deactivate as needed
```

## Database Tables

### purchased_processors

**Purpose**: Tenant-level processor subscriptions

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| organization_id | UUID | Tenant/org reference |
| processor | TEXT | Processor identifier (e.g., 'p_bank_statement') |
| name | TEXT | Display name |
| auto | BOOL | Auto-execute flag |
| status | TEXT | active, disabled, deleted |
| config | JSONB | Tenant configuration overrides |
| price_amount | BIGINT | Cost in cents |
| price_unit | TEXT | Per execution, page, document |
| purchased_at | TIMESTAMP | Purchase timestamp |
| purchased_by | UUID | User who purchased |

### underwriting_processors

**Purpose**: Underwriting-level processor configurations

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| organization_id | UUID | Tenant/org reference |
| underwriting_id | UUID | Underwriting case reference |
| purchased_processor_id | UUID | Link to purchased processor |
| processor | TEXT | Processor identifier |
| name | TEXT | Display name |
| auto | BOOL | Auto-execute for this underwriting |
| enabled | BOOL | Enable/disable flag |
| config_override | JSONB | Case-specific config overrides |
| effective_config | JSONB | Resolved configuration (computed) |
| current_executions_list | UUID[] | Active execution IDs |

### processor_executions

**Purpose**: Execution records with full audit trail

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| organization_id | UUID | Tenant/org reference |
| underwriting_id | UUID | Underwriting case reference |
| underwriting_processor_id | UUID | Processor config reference |
| processor | TEXT | Processor identifier |
| status | TEXT | pending, running, completed, failed |
| enabled | BOOL | Active in consolidation |
| payload | JSONB | Execution input |
| payload_hash | TEXT | Hash for deduplication |
| output | JSONB | Execution result |
| factors_delta | JSONB | Factors written by this execution |
| document_revision_ids | TEXT[] | Documents used |
| document_ids_hash | TEXT | Document set hash |
| run_cost_cents | BIGINT | Cost in cents |
| started_at | TIMESTAMP | Execution start time |
| completed_at | TIMESTAMP | Execution end time |
| failed_code | TEXT | Error code if failed |
| failed_reason | TEXT | Error message if failed |
| updated_execution_id | UUID | Supersession link |
| created_at | TIMESTAMP | Record creation time |
| updated_at | TIMESTAMP | Last update time |
| disabled_at | TIMESTAMP | Deactivation time |

## Usage Patterns

### Pattern 1: Get Processor Configuration

```python
from src.aura.processing_engine.repositories import ProcessorRepository

# Initialize repository
processor_repo = ProcessorRepository(db_connection)

# Get underwriting processor
up = processor_repo.get_underwriting_processor_by_id("up_123")

# Get effective configuration (merged)
config = processor_repo.get_effective_config("up_123")

# Use in BaseProcessor
processor_class.get_config(up)  # Returns merged config
```

### Pattern 2: Create and Track Execution

```python
from src.aura.processing_engine.repositories import ExecutionRepository

# Initialize repository
exec_repo = ExecutionRepository(db_connection)

# Check for duplicate
existing = exec_repo.find_execution_by_hash("up_123", "hash_abc")
if existing:
    return existing["id"]

# Create new execution
exec_id = exec_repo.create_execution(
    underwriting_id="uw_001",
    underwriting_processor_id="up_123",
    organization_id="org_456",
    processor_name="p_bank_statement",
    payload={"documents": [...]},
    payload_hash="hash_abc",
    document_revision_ids=["rev_001", "rev_002"],
    document_ids_hash="doc_hash_123"
)

# Update status to running
exec_repo.update_execution_status(
    exec_id,
    "running",
    started_at=datetime.utcnow()
)

# Save result
exec_repo.save_execution_result(
    exec_id,
    output={"monthly_revenues": [45000.0]},
    factors_delta={"f_avg_revenue": 45000.0},
    run_cost_cents=50,
    completed_at=datetime.utcnow()
)
```

### Pattern 3: Execution Deduplication

```python
# Generate payload hash
payload_hash = hashlib.sha256(
    json.dumps(payload, sort_keys=True).encode()
).hexdigest()

# Check if execution exists
existing = exec_repo.find_execution_by_hash("up_123", payload_hash)

if existing and existing["status"] == "completed":
    # Reuse existing execution
    return existing
else:
    # Create new execution
    exec_id = exec_repo.create_execution(...)
```

### Pattern 4: Get Active Executions for Consolidation

```python
# Get all active executions for a processor
active_executions = exec_repo.get_active_executions("up_123")

# These are executions that:
# - Have enabled = true
# - Are in current_executions_list
# - Have status = 'completed'

# Pass to processor's consolidate method
consolidated_factors = ProcessorClass.consolidate(
    [exec["output"] for exec in active_executions]
)
```

### Pattern 5: Supersession and Rollback

```python
# Create new execution that supersedes old one
new_exec_id = exec_repo.create_execution(...)

# Mark old execution as superseded
exec_repo.mark_execution_superseded(old_exec_id, new_exec_id)

# Later, if need to rollback:
exec_repo.activate_execution(old_exec_id)
exec_repo.deactivate_execution(new_exec_id)

# Update current execution list
processor_repo.update_current_executions_list(
    "up_123",
    [old_exec_id]  # Remove new_exec_id, add old_exec_id back
)
```

### Pattern 6: Filter Processors for Auto-Execution

```python
# Get all auto-enabled processors for an underwriting
processors = processor_repo.get_underwriting_processors(
    underwriting_id="uw_001",
    enabled_only=True,
    auto_only=True
)

# Execute each processor
for proc in processors:
    # Check if should execute
    if ProcessorClass.should_execute(payload, proc["effective_config"]):
        exec_id = exec_repo.create_execution(...)
```

## Testing

All repositories have comprehensive test coverage in `tests/unit/processing_engine/test_repositories.py`.

### Test Categories

1. **Structure Tests**: Verify repository initialization and method existence
2. **Catalog Tests**: System processor catalog operations
3. **Purchased Processor Tests**: Tenant-level subscription operations
4. **Underwriting Processor Tests**: Case-level configuration operations
5. **Execution Creation Tests**: Execution record creation and UUID generation
6. **Status Update Tests**: Execution lifecycle status tracking
7. **Retrieval Tests**: Execution querying and filtering
8. **Supersession Tests**: Execution chain management
9. **Activation Tests**: Execution enable/disable operations
10. **Pattern Tests**: Common usage pattern validation

### Running Tests

```bash
# Run all repository tests
pytest tests/unit/processing_engine/test_repositories.py -v

# Run specific test class
pytest tests/unit/processing_engine/test_repositories.py::TestProcessorConfiguration -v

# Run with coverage
pytest tests/unit/processing_engine/test_repositories.py --cov=src/aura/processing_engine/repositories
```

## Implementation Status

### Current State

- ✅ Repository classes defined with full method signatures
- ✅ Comprehensive test suite (57 tests)
- ✅ Documentation and usage patterns
- ⚠️ Database operations are placeholder (return None/False/[])

### Next Steps

1. **Database Integration**:
   - Implement PostgreSQL operations using psycopg2/SQLAlchemy
   - Implement BigQuery operations using google-cloud-bigquery
   - Add transaction management and error handling

2. **Query Implementation**:
   - Write SQL queries for PostgreSQL
   - Write BigQuery SQL/API calls
   - Add proper parameterization and injection prevention

3. **Connection Management**:
   - Add connection pooling
   - Implement retry logic for transient failures
   - Add database health checks

4. **Caching**:
   - Add Redis caching for frequently accessed configs
   - Implement cache invalidation strategies
   - Add TTL management

## Database Connection Strategy

The repositories are designed to be database-agnostic, supporting both PostgreSQL and BigQuery:

### PostgreSQL

```python
import psycopg2
from psycopg2.extras import RealDictCursor

conn = psycopg2.connect(
    host="localhost",
    port=5432,
    database="aura_underwriting",
    user="aura_user",
    password="aura_password",
    cursor_factory=RealDictCursor
)

processor_repo = ProcessorRepository(conn)
execution_repo = ExecutionRepository(conn)
```

### BigQuery

```python
from google.cloud import bigquery

client = bigquery.Client(
    project="aura-project",
    credentials=credentials
)

processor_repo = ProcessorRepository(client)
execution_repo = ExecutionRepository(client)
```

## Error Handling

Repositories should handle common database errors:

```python
try:
    result = processor_repo.get_purchased_processor_by_id(id)
except DatabaseConnectionError:
    # Retry or fail gracefully
except RecordNotFoundError:
    # Return None
except DatabaseTimeoutError:
    # Retry with exponential backoff
```

## Contributing

When adding new repository methods:

1. **Define clear method signatures** with type hints
2. **Add comprehensive docstrings** with args/returns documentation
3. **Write tests first** (TDD approach)
4. **Consider both PostgreSQL and BigQuery** implementations
5. **Add usage examples** to this README
6. **Update integration tests** if needed

## Related Documentation

- [Base Processor Specification](../README.md)
- [Database Schema](@aura-database-schema.mdc)
- [Processor Execution Flow](@aura-processor-execution.mdc)
- [Processor Orchestration](@aura-processor-orchestration.mdc)

