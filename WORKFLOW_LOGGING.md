# Workflow Execution Logging

This document describes all the stages and steps logged to the `test_workflow` table for debugging and tracking.

## Workflow 1: Automatic Execution

### Main Stages

#### 1. **Filtration** (Main Stage)
- **Purpose**: Determine which processors should run
- **Logged Data**:
  - Input: `underwriting_id`
  - Output: `processor_list`, `execution_list`
  - Metadata: `processors_found`, `executions_to_run`

#### 2. **Execution** (Main Stage)
- **Purpose**: Run pending processor executions
- **Logged Data**:
  - Input: `execution_list`
  - Output: `completed`, `failed`, `results`
  - Metadata: `total_executions`, `parallel_workers`

#### 3. **Consolidation** (Main Stage)
- **Purpose**: Aggregate execution results into factors
- **Logged Data**:
  - Input: `processor_list`
  - Output: `consolidated`, `results`
  - Metadata: `total_processors`, `factors_generated`

---

### Detailed Sub-Steps

#### Filtration Sub-Steps

##### **prepare_processor**
- **Purpose**: Determine if specific processor should participate
- **Logged For**: Each processor checked
- **Logged Data**:
  - Input: `underwriting_processor_id`, `processor_name`, `duplicate`
  - Output: `payload_list`, `execution_list`, `new_executions`, `deleted_executions`, `result`
  - Metadata: `payloads_generated`, `executions_created`, `new_executions`, `deleted_executions`
- **Result Values**:
  - `"NULL"` - No triggers matched
  - `"OK"` - Triggers matched and executions prepared

##### **generate_execution**
- **Purpose**: Create or reuse execution based on payload hash
- **Logged For**: Each payload processed
- **Logged Data**:
  - Input: `underwriting_processor_id`, `payload`, `duplicate`
  - Output: `execution_id`, `payload_hash`, `action`, `updated_execution_id`
  - Metadata: `existing_found`, `is_duplicate`, `processor`
- **Action Values**:
  - `"created_new"` - New execution created
  - `"reused_existing"` - Existing execution reused
  - `"duplicated"` - Duplicate execution created with link

---

#### Execution Sub-Steps

##### **run_execution**
- **Purpose**: Execute single processor and extract factors
- **Logged For**: Each execution run
- **Logged Data**:
  - Input: `execution_id`, `processor`, `underwriting_processor_id`, `input_payload`
  - Output:
    - **Success**: `result: "success"`, `output`, `cost_cents`
    - **Failed**: `result: "failed"`, `error`
    - **Exception**: `result: "exception"`, `error`
  - Metadata: `processor`, `payload_hash`, `exception_type` (if exception)
- **Status Values**:
  - `"completed"` - Execution successful
  - `"failed"` - Execution failed (business logic error or exception)

---

#### Consolidation Sub-Steps

##### **consolidate_processor**
- **Purpose**: Consolidate execution outputs into final factors
- **Logged For**: Each processor in consolidation
- **Logged Data**:
  - Input: `underwriting_processor_id`, `processor`, `active_execution_count`
  - Output:
    - **Success**: `result: "success"`, `factors`, `factor_count`
    - **Error**: `result: "error"`, `error`
  - Metadata: `processor`, `executions_used`, `execution_ids`, `exception_type` (if error)
- **Status Values**:
  - `"completed"` - Consolidation successful
  - `"failed"` - Consolidation failed

---

## Data Flow Example

```
Workflow 1 Triggered
    │
    ├─► filtration (main stage)
    │   └─► prepare_processor (for processor A)
    │       ├─► generate_execution (payload 1)
    │       ├─► generate_execution (payload 2)
    │       └─► generate_execution (payload 3)
    │   └─► prepare_processor (for processor B)
    │       └─► generate_execution (payload 1)
    │
    ├─► execution (main stage)
    │   ├─► run_execution (execution 1) ✅
    │   ├─► run_execution (execution 2) ✅
    │   ├─► run_execution (execution 3) ❌
    │   └─► run_execution (execution 4) ✅
    │
    └─► consolidation (main stage)
        ├─► consolidate_processor (processor A) ✅
        └─► consolidate_processor (processor B) ✅
```

---

## Querying Test Workflow Data

### Get All Stages for an Underwriting
```python
python view_test_workflow.py
```

### Get Specific Stage Data
```sql
SELECT * FROM test_workflow
WHERE underwriting_id = 'uw_id'
  AND stage = 'run_execution'
ORDER BY created_at DESC;
```

### Get Failed Steps
```sql
SELECT * FROM test_workflow
WHERE status = 'failed'
ORDER BY created_at DESC;
```

### Get Execution Performance
```sql
SELECT 
    stage,
    AVG(execution_time_ms) as avg_time,
    MIN(execution_time_ms) as min_time,
    MAX(execution_time_ms) as max_time,
    COUNT(*) as count
FROM test_workflow
WHERE workflow_name = 'Workflow 1'
GROUP BY stage
ORDER BY avg_time DESC;
```

---

## Benefits

✅ **Complete Visibility**: Every step is tracked with inputs, outputs, and timing
✅ **Error Tracking**: Failed steps include error messages and exception types
✅ **Performance Analysis**: Execution time tracked for every step
✅ **Debugging**: Can replay exact payloads and see what happened
✅ **Audit Trail**: Complete history of all workflow executions
✅ **Optimization**: Identify slow steps and bottlenecks

---

## Notes

- All timestamps are in UTC
- Execution times are in milliseconds
- Payload hashes are SHA-256 (first 16 chars shown)
- Status is either `completed` or `failed`
- Output is stored as JSONB for flexible querying
- Metadata provides additional context-specific information

