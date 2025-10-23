-- Test Workflow Tracking Table
-- Tracks workflow execution stages for debugging and testing

CREATE TABLE IF NOT EXISTS test_workflow (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    underwriting_id UUID NOT NULL,
    workflow_name TEXT NOT NULL,  -- e.g., 'Workflow 1', 'Workflow 2'
    stage TEXT NOT NULL,           -- e.g., 'filtration', 'execution', 'consolidation'
    payload JSONB NOT NULL,        -- Input data for this stage
    payload_hash TEXT,             -- Hash of payload for deduplication tracking
    output JSONB,                  -- Output/result of this stage
    status TEXT NOT NULL CHECK (status IN ('started', 'completed', 'failed')),
    error_message TEXT,            -- Error details if failed
    execution_time_ms INTEGER,     -- How long this stage took
    metadata JSONB,                -- Additional debug info (processor_list, execution_list, etc.)
    created_at TIMESTAMP NOT NULL DEFAULT now(),
    updated_at TIMESTAMP NOT NULL DEFAULT now()
);

-- Indexes for querying
CREATE INDEX IF NOT EXISTS idx_test_workflow_underwriting ON test_workflow(underwriting_id);
CREATE INDEX IF NOT EXISTS idx_test_workflow_workflow_stage ON test_workflow(workflow_name, stage);
CREATE INDEX IF NOT EXISTS idx_test_workflow_created ON test_workflow(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_test_workflow_hash ON test_workflow(payload_hash);

-- Comments
COMMENT ON TABLE test_workflow IS 'Tracks workflow execution stages for debugging and testing orchestration flows';
COMMENT ON COLUMN test_workflow.stage IS 'Workflow stage: filtration, prepare_processor, generate_execution, execution, run_execution, consolidation';
COMMENT ON COLUMN test_workflow.payload IS 'Input data for this stage';
COMMENT ON COLUMN test_workflow.payload_hash IS 'Hash of payload for tracking deduplication logic';
COMMENT ON COLUMN test_workflow.output IS 'Result/output of this stage execution';
COMMENT ON COLUMN test_workflow.metadata IS 'Additional context: processor_list, execution_list, counts, etc.';

