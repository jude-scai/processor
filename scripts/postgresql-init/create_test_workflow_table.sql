-- Test Workflow Tracking Table
-- Tracks workflow execution stages for debugging and testing

CREATE TABLE IF NOT EXISTS test_workflow (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    underwriting_id UUID NOT NULL,
    workflow_name TEXT NOT NULL,  -- e.g., 'Workflow 1', 'Workflow 2'
    stage TEXT NOT NULL,           -- e.g., 'filtration', 'execution', 'consolidation'
    payload JSONB NOT NULL,        -- Parameters/arguments for this stage
    input JSONB,                   -- Actual input data being processed
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
COMMENT ON COLUMN test_workflow.stage IS 'Workflow stage: filtration, prepare_processor, format_payload_list, generate_execution, execution, run_execution, consolidation';
COMMENT ON COLUMN test_workflow.payload IS 'Parameters/arguments passed to this stage (e.g., underwriting_id, processor_id, flags)';
COMMENT ON COLUMN test_workflow.input IS 'Actual input data being processed (e.g., eligible processors, underwriting data, payload to hash)';
COMMENT ON COLUMN test_workflow.payload_hash IS 'Hash of payload for tracking deduplication logic';
COMMENT ON COLUMN test_workflow.output IS 'Result/output produced by this stage (e.g., processor_list, execution_list, generated payloads)';
COMMENT ON COLUMN test_workflow.metadata IS 'Additional context: counts, flags, processor details, etc.';

