-- ============================================================================
-- AURA Underwriting System - BigQuery Schema
-- ============================================================================
-- Note: BigQuery uses Standard SQL with some differences from PostgreSQL

-- ============================================================================
-- 1) Identity, Tenancy, Auth & RBAC
-- ============================================================================

-- Organization table
CREATE TABLE IF NOT EXISTS `aura-project.underwriting_data.organization` (
    id STRING NOT NULL,
    name STRING NOT NULL,
    status STRING NOT NULL DEFAULT 'active',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP(),
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP()
)
OPTIONS(
    description="Multi-tenant organizations"
);

-- Account (user) table
CREATE TABLE IF NOT EXISTS `aura-project.underwriting_data.account` (
    id STRING NOT NULL,
    organization_id STRING NOT NULL,
    firebase_uid STRING NOT NULL,
    email STRING NOT NULL,
    first_name STRING,
    last_name STRING,
    status STRING NOT NULL DEFAULT 'active',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP(),
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP()
)
OPTIONS(
    description="User accounts with Firebase authentication"
);

-- Role table
CREATE TABLE IF NOT EXISTS `aura-project.underwriting_data.role` (
    id STRING NOT NULL,
    name STRING NOT NULL,
    description STRING,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP(),
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP()
)
OPTIONS(
    description="User roles for RBAC"
);

-- Permission table
CREATE TABLE IF NOT EXISTS `aura-project.underwriting_data.permission` (
    id STRING NOT NULL,
    name STRING NOT NULL,
    description STRING
)
OPTIONS(
    description="Granular permissions catalog"
);

-- Role-Permission mapping
CREATE TABLE IF NOT EXISTS `aura-project.underwriting_data.role_permission` (
    role_id STRING NOT NULL,
    permission_id STRING NOT NULL
)
OPTIONS(
    description="Assign permissions to roles"
);

-- Account-Role mapping
CREATE TABLE IF NOT EXISTS `aura-project.underwriting_data.account_role` (
    account_id STRING NOT NULL,
    role_id STRING NOT NULL
)
OPTIONS(
    description="Assign roles to accounts"
);

-- Organization invitation table
CREATE TABLE IF NOT EXISTS `aura-project.underwriting_data.organization_invitation` (
    id STRING NOT NULL,
    organization_id STRING NOT NULL,
    email STRING NOT NULL,
    role_name STRING NOT NULL,
    token_hash STRING NOT NULL,
    status STRING NOT NULL,
    invited_by STRING NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    accepted_at TIMESTAMP,
    account_id STRING,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP()
)
OPTIONS(
    description="Invite-based onboarding"
);

-- Idempotency key table
CREATE TABLE IF NOT EXISTS `aura-project.underwriting_data.idempotency_key` (
    organization_id STRING NOT NULL,
    scope STRING NOT NULL,
    key STRING NOT NULL,
    response_hash STRING,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP()
)
OPTIONS(
    description="Request-level idempotency"
);

-- ============================================================================
-- 2) Core Underwriting & Application Data
-- ============================================================================

-- Underwriting root aggregate
CREATE TABLE IF NOT EXISTS `aura-project.underwriting_data.underwriting` (
    id STRING NOT NULL,
    organization_id STRING NOT NULL,
    serial_number STRING NOT NULL,
    status STRING NOT NULL,
    application_type STRING,
    application_ref_id STRING,
    request_amount NUMERIC(15,2),
    request_date DATE,
    purpose STRING,
    -- ISO details
    iso_ref_id STRING,
    iso_name STRING,
    iso_email STRING,
    iso_phone STRING,
    -- Representative details
    representative_ref_id STRING,
    representative_first_name STRING,
    representative_last_name STRING,
    representative_email STRING,
    representative_phone_mobile STRING,
    representative_phone_home STRING,
    representative_phone_work STRING,
    -- Merchant details
    merchant_ref_id STRING,
    merchant_name STRING,
    merchant_dba_name STRING,
    merchant_email STRING,
    merchant_phone STRING,
    merchant_website STRING,
    merchant_industry STRING,
    merchant_ein STRING,
    merchant_entity_type STRING,
    merchant_incorporation_date DATE,
    merchant_state_of_incorporation STRING,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP(),
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP(),
    created_by STRING NOT NULL,
    updated_by STRING NOT NULL
)
OPTIONS(
    description="Main underwriting records"
);

-- Merchant address
CREATE TABLE IF NOT EXISTS `aura-project.underwriting_data.merchant_address` (
    id STRING NOT NULL,
    underwriting_id STRING NOT NULL,
    addr_1 STRING,
    addr_2 STRING,
    city STRING,
    state STRING,
    zip STRING,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP(),
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP(),
    created_by STRING NOT NULL,
    updated_by STRING NOT NULL
)
OPTIONS(
    description="Merchant business addresses"
);

-- Owner (beneficial owners)
CREATE TABLE IF NOT EXISTS `aura-project.underwriting_data.owner` (
    id STRING NOT NULL,
    underwriting_id STRING NOT NULL,
    first_name STRING,
    last_name STRING,
    email STRING,
    phone_mobile STRING,
    phone_work STRING,
    phone_home STRING,
    birthday DATE,
    fico_score INT64,
    ssn STRING,
    enabled BOOL NOT NULL DEFAULT TRUE,
    ownership_percent NUMERIC(5,2),
    primary_owner BOOL DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP(),
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP(),
    created_by STRING NOT NULL,
    updated_by STRING NOT NULL
)
OPTIONS(
    description="Beneficial owners"
);

-- Owner address
CREATE TABLE IF NOT EXISTS `aura-project.underwriting_data.owner_address` (
    id STRING NOT NULL,
    owner_id STRING NOT NULL,
    addr_1 STRING,
    addr_2 STRING,
    city STRING,
    state STRING,
    zip STRING,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP(),
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP(),
    created_by STRING NOT NULL,
    updated_by STRING NOT NULL
)
OPTIONS(
    description="Owner addresses"
);

-- Document (artifact pointer + classification)
CREATE TABLE IF NOT EXISTS `aura-project.underwriting_data.document` (
    id STRING NOT NULL,
    organization_id STRING NOT NULL,
    underwriting_id STRING NOT NULL,
    status STRING NOT NULL,
    current_revision_id STRING,
    stipulation_type STRING,
    classification_confidence NUMERIC(5,2),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP(),
    created_by STRING NOT NULL,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP(),
    updated_by STRING
)
OPTIONS(
    description="Document metadata and classification"
);

-- Document revision (upload/replace history)
CREATE TABLE IF NOT EXISTS `aura-project.underwriting_data.document_revision` (
    id STRING NOT NULL,
    document_id STRING NOT NULL,
    revision INT64 NOT NULL,
    gcs_uri STRING NOT NULL,
    ocr_gcs_uri STRING,
    filename STRING NOT NULL,
    mime_type STRING NOT NULL,
    size_bytes INT64 NOT NULL,
    gcs_generation INT64,
    crc32c STRING,
    md5 STRING,
    quality_score NUMERIC(5,2),
    dpi_x INT64,
    dpi_y INT64,
    page_count INT64,
    rejection_code STRING,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP(),
    created_by STRING,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP(),
    updated_by STRING
)
OPTIONS(
    description="Document revision history"
);

-- ============================================================================
-- 3) Processing, Catalog, Executions, Costs
-- ============================================================================

-- Organization processors (entitlements)
CREATE TABLE IF NOT EXISTS `aura-project.underwriting_data.organization_processors` (
    id STRING NOT NULL,
    organization_id STRING NOT NULL,
    processor STRING NOT NULL,
    name STRING NOT NULL,
    auto BOOL NOT NULL DEFAULT TRUE,
    price_amount INT64,
    price_unit STRING,
    price_currency STRING NOT NULL DEFAULT 'USD',
    purchased_by STRING NOT NULL,
    purchased_at TIMESTAMP NOT NULL,
    status STRING NOT NULL,
    config JSON,
    notes STRING,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP(),
    created_by STRING,
    disabled_at TIMESTAMP,
    disabled_by STRING,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP(),
    updated_by STRING
)
OPTIONS(
    description="Processor entitlements per organization"
);

-- Underwriting processors (selection/override per underwriting)
CREATE TABLE IF NOT EXISTS `aura-project.underwriting_data.underwriting_processors` (
    id STRING NOT NULL,
    organization_id STRING NOT NULL,
    underwriting_id STRING NOT NULL,
    organization_processor_id STRING,
    current_executions_list ARRAY<STRING>,
    processor STRING NOT NULL,
    name STRING NOT NULL,
    auto BOOL,
    notes STRING,
    enabled BOOL NOT NULL DEFAULT TRUE,
    config_override JSON,
    effective_config JSON,
    price_snapshot_amount INT64,
    price_snapshot_unit STRING,
    price_snapshot_currency STRING,
    created_by STRING,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP(),
    disabled_at TIMESTAMP,
    disabled_by STRING,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP(),
    updated_by STRING
)
OPTIONS(
    description="Processors enabled per underwriting"
);

-- Processor executions (single processor attempt per record)
CREATE TABLE IF NOT EXISTS `aura-project.underwriting_data.processor_executions` (
    id STRING NOT NULL,
    organization_id STRING NOT NULL,
    underwriting_id STRING NOT NULL,
    organization_processor_id STRING,
    underwriting_processor_id STRING NOT NULL,
    document_id STRING,
    processor STRING NOT NULL,
    status STRING NOT NULL,
    enabled BOOL DEFAULT TRUE,
    factors_delta JSON,
    payload JSON,
    payload_hash STRING,
    run_cost_cents INT64,
    currency STRING NOT NULL DEFAULT 'USD',
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    failed_code STRING,
    failed_reason STRING,
    created_by STRING,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP(),
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP(),
    disabled_at TIMESTAMP,
    disabled_by STRING,
    updated_by STRING,
    updated_execution_id STRING
)
OPTIONS(
    description="Processor execution tracking"
);

-- ============================================================================
-- 4) Factors
-- ============================================================================

-- Factor (atomic factors per underwriting)
CREATE TABLE IF NOT EXISTS `aura-project.underwriting_data.factor` (
    id STRING NOT NULL,
    organization_id STRING NOT NULL,
    underwriting_id STRING NOT NULL,
    factor_key STRING NOT NULL,
    value JSON NOT NULL,
    unit STRING,
    source STRING NOT NULL,
    status STRING NOT NULL,
    factor_hash STRING,
    underwriting_processor_id STRING,
    execution_id STRING,
    created_by STRING,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP(),
    updated_by STRING,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP(),
    updated_factor_id STRING
)
OPTIONS(
    description="Atomic factors per underwriting"
);

-- Factor snapshot
CREATE TABLE IF NOT EXISTS `aura-project.underwriting_data.factor_snapshot` (
    id STRING NOT NULL,
    organization_id STRING NOT NULL,
    underwriting_id STRING NOT NULL,
    snapshot_hash STRING NOT NULL,
    data JSON NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP(),
    created_by STRING NOT NULL,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP(),
    updated_by STRING
)
OPTIONS(
    description="Point-in-time factor snapshots"
);

-- ============================================================================
-- 5) Pre-Check Rules & Evaluations
-- ============================================================================

-- Pre-check rule
CREATE TABLE IF NOT EXISTS `aura-project.underwriting_data.precheck_rule` (
    id STRING NOT NULL,
    organization_id STRING NOT NULL,
    name STRING NOT NULL,
    description STRING,
    status STRING NOT NULL,
    criterion JSON NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP(),
    effective_at TIMESTAMP,
    expires_at TIMESTAMP,
    version INT64 NOT NULL,
    updated_by STRING,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP(),
    created_by STRING NOT NULL
)
OPTIONS(
    description="Business validation rules"
);

-- Pre-check evaluation
CREATE TABLE IF NOT EXISTS `aura-project.underwriting_data.precheck_evaluation` (
    id STRING NOT NULL,
    organization_id STRING NOT NULL,
    underwriting_id STRING NOT NULL,
    factor_snapshot_id STRING NOT NULL,
    status STRING NOT NULL,
    failures JSON NOT NULL,
    skipped JSON NOT NULL,
    rule_version INT64,
    evaluation_source STRING DEFAULT 'processor',
    evaluation_message_id STRING,
    evaluated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP(),
    created_by STRING,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP(),
    updated_by STRING
)
OPTIONS(
    description="Rule evaluation results"
);

-- ============================================================================
-- 6) Score Card Config & Scores
-- ============================================================================

-- Scorecard config
CREATE TABLE IF NOT EXISTS `aura-project.underwriting_data.scorecard_config` (
    id STRING NOT NULL,
    organization_id STRING NOT NULL,
    version INT64 NOT NULL,
    config JSON NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP(),
    created_by STRING,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP(),
    updated_by STRING
)
OPTIONS(
    description="Scoring configurations"
);

-- Underwriting score
CREATE TABLE IF NOT EXISTS `aura-project.underwriting_data.underwriting_score` (
    id STRING NOT NULL,
    organization_id STRING NOT NULL,
    underwriting_id STRING NOT NULL,
    factor_snapshot_id STRING NOT NULL,
    scorecard_version INT64 NOT NULL,
    score INT64 NOT NULL,
    grade STRING NOT NULL,
    expected_loss NUMERIC(6,3),
    raw_points INT64,
    top_reasons JSON,
    missing_factors JSON,
    evaluated_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP(),
    created_by STRING,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP(),
    updated_by STRING
)
OPTIONS(
    description="Underwriting score results"
);

-- ============================================================================
-- 7) Suggestions & Decisions
-- ============================================================================

-- Suggestion
CREATE TABLE IF NOT EXISTS `aura-project.underwriting_data.suggestion` (
    id STRING NOT NULL,
    organization_id STRING NOT NULL,
    underwriting_id STRING NOT NULL,
    status STRING NOT NULL,
    notes STRING,
    payload JSON,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP(),
    created_by STRING,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP(),
    updated_by STRING
)
OPTIONS(
    description="AI-generated suggestions"
);

-- Decision
CREATE TABLE IF NOT EXISTS `aura-project.underwriting_data.decision` (
    id STRING NOT NULL,
    organization_id STRING NOT NULL,
    underwriting_id STRING NOT NULL,
    decision STRING NOT NULL,
    amount_approved NUMERIC(15,2),
    reasoning JSON,
    funded_amount NUMERIC(15,2),
    payback_amount NUMERIC(15,2),
    terms INT64,
    frequency STRING NOT NULL,
    suggestion_id STRING NOT NULL,
    decision_maker STRING NOT NULL,
    decided_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP(),
    created_by STRING,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP(),
    updated_by STRING
)
OPTIONS(
    description="Final human decisions"
);

