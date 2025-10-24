# Failed Execution Consolidation Strategy

## Overview

This document outlines the strategy for handling failed executions during the consolidation phase. Failed executions should be considered "active" but contribute no factors to the final consolidation result.

## Problem Statement

When processor executions fail, the current system excludes them from consolidation entirely, resulting in "0 active executions" and potential factor clearing. However, failed executions should be treated as active participants in the consolidation process, even though they contribute no meaningful data.

## Proposed Solution

### 1. Failed Executions as Active Participants

**Failed executions should be considered "active"** for the following reasons:

- **Audit Trail**: Maintains complete execution history for debugging and compliance
- **State Tracking**: Shows that the processor was attempted but failed
- **Consolidation Logic**: Allows consolidation to proceed even with failed executions
- **Factor Management**: Enables proper factor clearing when all executions fail

### 2. Consolidation Behavior for Failed Executions

#### **Document Type Processors**
- **Failed Execution**: Contributes empty factors (cleared state)
- **Successful Executions**: Contribute their factors normally
- **Consolidation Result**: Factors from successful executions + empty factors from failed executions
- **No Error**: Consolidation succeeds with failed executions as active participants

#### **Application Type Processors**
- **Failed Execution**: Contributes no factors
- **Consolidation Result**: Empty factors if all executions failed, or factors from successful executions
- **Factor Clearing**: If all executions failed, factors are cleared (not an error)

#### **Stipulation Type Processors**
- **Failed Execution**: Contributes no factors
- **Consolidation Result**: Aggregated factors from successful executions only
- **Partial Success**: If some executions succeed and others fail, only successful factors are used

### 3. Implementation Strategy

#### **Database Query Modification**
```sql
-- Current query (excludes failed executions):
WHERE pe.status = 'completed'

-- Proposed query (includes failed executions):
WHERE pe.status IN ('completed', 'failed')
```

#### **Consolidation Logic Enhancement**
```python
def consolidate(executions: list[ExecutionRecord]) -> dict[str, Any]:
    """
    Enhanced consolidation that processes ALL active executions (successful + failed).
    Failed executions contribute empty factors (not an error).
    """
    if not executions:
        return {}
    
    consolidated_factors = {}
    
    for execution in executions:
        if execution.status == 'completed' and execution.output:
            # Successful execution - contribute its factors
            factors = execution.output.get('factors', {})
            consolidated_factors.update(factors)
        elif execution.status == 'failed':
            # Failed execution - contributes empty factors (cleared)
            # This is NOT an error - it's a valid execution with no factors
            pass  # No factors to add, but execution is still "active"
    
    return consolidated_factors
```

### 4. Benefits of This Approach

#### **Improved Debugging**
- Failed executions remain visible in consolidation logs
- Easier to identify which processors failed and why
- Complete execution history for troubleshooting

#### **Better State Management**
- Consolidation always runs, even with failed executions
- Factors are properly managed (cleared when all fail, partial when some fail)
- No "0 active executions" confusion

#### **Enhanced Monitoring**
- Can track failure rates per processor
- Better visibility into system health
- Improved alerting and diagnostics

### 5. Example Scenarios

#### **Scenario 1: Mixed Success/Failure**
```
Bank Statement Processor:
- Execution 1: SUCCESS → Revenue: $10,000
- Execution 2: FAILED → No output
- Execution 3: SUCCESS → Revenue: $12,000

Consolidation Result:
- f_revenue_monthly_avg: $11,000 (from successful executions only)
- f_months_analyzed: 2 (only successful executions counted)
```

#### **Scenario 2: All Executions Failed**
```
Credit Check Processor:
- Execution 1: FAILED → No output
- Execution 2: FAILED → No output

Consolidation Result:
- Empty factors (not an error)
- Factors cleared from database
- Consolidation completes successfully
```

#### **Scenario 3: Document Processor with Mixed Results**
```
Driver's License Processor:
- Execution 1: SUCCESS → License verified
- Execution 2: FAILED → No output
- Execution 3: SUCCESS → License verified

Consolidation Result:
- f_verified_licenses_count: 2
- f_total_licenses_processed: 2 (only successful executions)
```

### 6. Implementation Requirements

#### **Database Changes**
1. Modify `get_active_executions()` query to include failed executions
2. Update consolidation logic to filter successful executions
3. Ensure failed executions don't contribute null factors

#### **Processor Changes**
1. Update consolidation methods to handle failed executions
2. Implement graceful handling of empty/null outputs
3. Maintain audit trail of failed executions

#### **Monitoring Changes**
1. Add logging for failed execution handling
2. Track consolidation success rates
3. Monitor factor quality and completeness

### 7. Migration Strategy

#### **Phase 1: Database Query Updates**
- Modify `ExecutionRepository.get_active_executions()`
- Include failed executions in active execution list
- Test with existing processors

#### **Phase 2: Consolidation Logic Updates**
- Update processor consolidation methods
- Implement failed execution filtering
- Add comprehensive logging

#### **Phase 3: Monitoring and Validation**
- Add monitoring for failed execution handling
- Validate factor quality and completeness
- Update documentation and runbooks

### 8. Risk Mitigation

#### **Data Quality**
- Failed executions never contribute null factors
- Consolidation always produces valid results
- Factor validation ensures data integrity

#### **Performance**
- Minimal performance impact
- Failed executions are filtered efficiently
- No additional database queries required

#### **Backward Compatibility**
- Existing successful consolidations unchanged
- Failed execution handling is additive
- No breaking changes to current behavior

## Conclusion

Treating failed executions as active participants in consolidation provides better debugging capabilities, improved state management, and enhanced monitoring while maintaining data integrity. The approach ensures that consolidation always completes successfully, even when some or all executions fail, without compromising the quality of the resulting factors.
