# Processing Engine - Complete Guide

## Quick Start

```bash
# 1. Verify setup
python verify_test_processor.py

# 2. Start API
python api.py

# 3. Test workflow
./test_api_workflow1.sh
```

## Architecture

### Service Structure

```
services/
├── orchestrator.py    # Main workflow coordinator (class)
├── filtration.py      # Plain functions: filtration(), prepare_processor(), generate_execution()
├── execution.py       # Plain functions: execution(), run_single_execution()
└── consolidation.py   # Plain function: consolidation()

utils/
├── payload.py         # Payload formatting utilities
└── hashing.py         # Consistent hash generation
```

**Services use plain functions** for simplicity and explicit dependencies.

### Workflow 1 Flow

```
Filtration → Execution → Consolidation
    ↓            ↓             ↓
  4 stages    2 stages      2 stages
```

## Filtration Service

### Logged Stages (Input/Output Pairs)

Each major step logs **input** and **output** separately for complete visibility:

1. **filtration_input** - Eligible processors loaded (enabled=true, auto=true)
2. **filtration** - Main workflow result (processor_list, execution_list)
3. **prepare_processor_input** - Processor config + underwriting data
4. **format_payload_list_input** - Underwriting data available for formatting
5. **format_payload_list_output** - Generated payloads
6. **prepare_processor_output** - Execution list built
7. **generate_execution_input** - Payload to be hashed
8. **generate_execution_output** - Execution created/reused

**Total per processor:** ~7 logs (input + output for each step)

### Quick Test

```bash
./test_api_workflow1.sh
```

### Verification Query

```sql
SELECT stage, COUNT(*) as count 
FROM test_workflow 
WHERE underwriting_id = 'your-id'
GROUP BY stage;
```

## API Endpoints

### POST /trigger/workflow1

```bash
curl -X POST http://localhost:8000/trigger/workflow1 \
  -H "Content-Type: application/json" \
  -d '{"underwriting_id": "uw_123"}'
```

**Response:**
```json
{
  "success": true,
  "processors_selected": 1,
  "executions_run": 1,
  "test_workflow_logged": true
}
```

## Consistent Hashing

### How It Works

```python
# Keys sorted lexicographically, nested structures normalized
payload1 = {"b": 2, "a": 1}
payload2 = {"a": 1, "b": 2}

# Same hash regardless of key order ✅
assert generate_payload_hash(payload1) == generate_payload_hash(payload2)
```

### Guarantees

- ✅ Dictionary keys sorted alphabetically
- ✅ Nested dictionaries normalized recursively
- ✅ Lists preserve order
- ✅ Sets converted to sorted lists
- ✅ Special types (datetime, Decimal) handled

### Test

```bash
python test_consistent_hashing.py
```

## Test Processor

### TestApplicationProcessor

**Location:** `src/aura/processing_engine/processors/test_processor.py`

**Config:**
- Name: `p_test_application`
- Type: APPLICATION
- Triggers: `["merchant.name", "merchant.ein"]`

**Factors:**
- `f_merchant_name`
- `f_merchant_ein`
- `f_merchant_industry`
- `f_merchant_state`
- `f_merchant_entity_type`
- `f_owner_count`
- `f_primary_owner_name`

## Adding Processors

```python
# 1. Create processor
# src/aura/processing_engine/processors/my_processor.py
from ..base_processor import BaseProcessor
from ..models import ProcessorType

class MyProcessor(BaseProcessor):
    PROCESSOR_NAME = "p_my_processor"
    PROCESSOR_TYPE = ProcessorType.APPLICATION
    PROCESSOR_TRIGGERS = {"application_form": ["field1"]}
    
    def transform_input(self, payload): ...
    def validate_input(self, data): ...
    def extract(self, data): ...
    def validate_output(self, output): ...

# 2. Export from __init__.py
from .my_processor import MyProcessor
__all__ = ["TestApplicationProcessor", "MyProcessor"]

# 3. Register in API
service.register_processor("p_my_processor", MyProcessor)
```

## Test Scripts

- `verify_test_processor.py` - Verify processor setup
- `test_consistent_hashing.py` - Test hash consistency
- `test_api_workflow1.sh` - Test API endpoint
- `test_filtration_logging.py` - Test filtration stages
- `query_filtration_logs.sql` - SQL queries for verification

## Troubleshooting

### No test_workflow logs
- Check API response shows `test_workflow_logged: true`
- Verify test_workflow table exists
- Check processor is registered

### Import errors
```bash
python verify_test_processor.py
```

### API not responding
```bash
curl http://localhost:8000/health
```

### No processors running
- Check processor enabled in database
- Verify underwriting has trigger data
- Check processor registration

## Database

### Tables
- `underwriting_processors` - Processor configuration
- `processor_executions` - Execution records
- `test_workflow` - Stage logging

### Check Logs
```sql
SELECT * FROM test_workflow 
WHERE underwriting_id = 'your-id'
ORDER BY created_at;
```

## Performance

- Parallel execution: Max 5 concurrent
- Hash deduplication: Prevents duplicate work
- Test logging: ~5-10ms overhead per stage
- Disable in production: `enable_test_tracking=False`

