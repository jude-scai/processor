-- AURA Underwriting System Database Schema
-- PostgreSQL initialization script

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================================
-- 1) Identity, Tenancy, Auth & RBAC
-- ============================================================================

-- Organization table
CREATE TABLE organization (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'suspended', 'deleted')),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Account (user) table
CREATE TABLE account (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES organization(id),
    firebase_uid TEXT NOT NULL UNIQUE,
    email TEXT NOT NULL,
    first_name TEXT,
    last_name TEXT,
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'invited', 'disabled')),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE (organization_id, email)
);

-- Role table
CREATE TABLE role (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Permission table
CREATE TABLE permission (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL UNIQUE,
    description TEXT
);

-- Role-Permission mapping
CREATE TABLE role_permission (
    role_id UUID NOT NULL REFERENCES role(id) ON DELETE CASCADE,
    permission_id UUID NOT NULL REFERENCES permission(id) ON DELETE CASCADE,
    PRIMARY KEY (role_id, permission_id)
);

-- Account-Role mapping
CREATE TABLE account_role (
    account_id UUID NOT NULL REFERENCES account(id) ON DELETE CASCADE,
    role_id UUID NOT NULL REFERENCES role(id) ON DELETE CASCADE,
    PRIMARY KEY (account_id, role_id)
);

-- Organization invitation table
CREATE TABLE organization_invitation (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES organization(id),
    email TEXT NOT NULL,
    role_name TEXT NOT NULL CHECK (role_name IN ('MANAGER', 'UNDERWRITER', 'VIEWER')),
    token_hash TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('pending', 'accepted', 'expired')),
    invited_by UUID NOT NULL REFERENCES account(id),
    expires_at TIMESTAMP NOT NULL,
    accepted_at TIMESTAMP,
    account_id UUID REFERENCES account(id),
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Idempotency key table
CREATE TABLE idempotency_key (
    organization_id UUID NOT NULL REFERENCES organization(id),
    scope TEXT NOT NULL,
    key TEXT NOT NULL,
    response_hash TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    PRIMARY KEY (organization_id, scope, key)
);

-- ============================================================================
-- 2) Core Underwriting & Application Data
-- ============================================================================

-- Underwriting root aggregate
CREATE TABLE underwriting (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES organization(id),
    serial_number TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('created', 'processing', 'rejected', 'missing', 'passed', 'suggested', 'decided', 'cancelled', 'deleted')),
    application_type TEXT CHECK (application_type IN ('NEW', 'RENEWAL')),
    application_ref_id TEXT,
    request_amount NUMERIC(15,2),
    request_date DATE,
    purpose TEXT,
    -- ISO details
    iso_ref_id TEXT,
    iso_name TEXT,
    iso_email TEXT,
    iso_phone TEXT,
    -- Representative details
    representative_ref_id TEXT,
    representative_first_name TEXT,
    representative_last_name TEXT,
    representative_email TEXT,
    representative_phone_mobile TEXT,
    representative_phone_home TEXT,
    representative_phone_work TEXT,
    -- Merchant details
    merchant_ref_id TEXT,
    merchant_name TEXT,
    merchant_dba_name TEXT,
    merchant_email TEXT,
    merchant_phone TEXT,
    merchant_website TEXT,
    merchant_industry TEXT,
    merchant_ein TEXT,
    merchant_entity_type TEXT,
    merchant_incorporation_date DATE,
    merchant_state_of_incorporation TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    created_by UUID NOT NULL REFERENCES account(id),
    updated_by UUID NOT NULL REFERENCES account(id)
);

-- Merchant address
CREATE TABLE merchant_address (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    underwriting_id UUID NOT NULL REFERENCES underwriting(id) ON DELETE CASCADE,
    addr_1 TEXT,
    addr_2 TEXT,
    city TEXT,
    state TEXT,
    zip TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    created_by UUID NOT NULL REFERENCES account(id),
    updated_by UUID NOT NULL REFERENCES account(id)
);

-- Owner (beneficial owners)
CREATE TABLE owner (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    underwriting_id UUID NOT NULL REFERENCES underwriting(id) ON DELETE CASCADE,
    first_name TEXT,
    last_name TEXT,
    email TEXT,
    phone_mobile TEXT,
    phone_work TEXT,
    phone_home TEXT,
    birthday DATE,
    fico_score INT,
    ssn TEXT,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    ownership_percent NUMERIC(5,2),
    primary_owner BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    created_by UUID NOT NULL REFERENCES account(id),
    updated_by UUID NOT NULL REFERENCES account(id)
);

-- Owner address
CREATE TABLE owner_address (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    owner_id UUID NOT NULL REFERENCES owner(id) ON DELETE CASCADE,
    addr_1 TEXT,
    addr_2 TEXT,
    city TEXT,
    state TEXT,
    zip TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    created_by UUID NOT NULL REFERENCES account(id),
    updated_by UUID NOT NULL REFERENCES account(id)
);

-- Document (artifact pointer + classification)
CREATE TABLE document (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES organization(id),
    underwriting_id UUID NOT NULL REFERENCES underwriting(id) ON DELETE CASCADE,
    status TEXT NOT NULL CHECK (status IN ('uploaded', 'accepted', 'rejected', 'deleted')),
    current_revision_id UUID,
    stipulation_type TEXT,
    classification_confidence NUMERIC(5,2),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    created_by UUID NOT NULL REFERENCES account(id),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_by UUID REFERENCES account(id)
);

-- Document revision (upload/replace history)
CREATE TABLE document_revision (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID NOT NULL REFERENCES document(id) ON DELETE CASCADE,
    revision INT NOT NULL,
    gcs_uri TEXT NOT NULL,
    ocr_gcs_uri TEXT,
    filename TEXT NOT NULL,
    mime_type TEXT NOT NULL,
    size_bytes BIGINT NOT NULL,
    gcs_generation BIGINT,
    crc32c TEXT,
    md5 TEXT,
    quality_score NUMERIC(5,2),
    dpi_x INT,
    dpi_y INT,
    page_count INT,
    rejection_code TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    created_by UUID REFERENCES account(id),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_by UUID REFERENCES account(id),
    UNIQUE (document_id, revision)
);

-- ============================================================================
-- 3) Processing, Catalog, Executions, Costs
-- ============================================================================

-- Organization processors (entitlements)
CREATE TABLE organization_processors (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES organization(id),
    processor TEXT NOT NULL,
    name TEXT NOT NULL,
    auto BOOLEAN NOT NULL DEFAULT TRUE,
    price_amount BIGINT,
    price_unit TEXT,
    price_currency TEXT NOT NULL DEFAULT 'USD',
    purchased_by UUID NOT NULL REFERENCES account(id),
    purchased_at TIMESTAMP NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('active', 'disabled', 'deleted')),
    config JSONB,
    notes TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    created_by UUID REFERENCES account(id),
    disabled_at TIMESTAMP,
    disabled_by UUID REFERENCES account(id),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_by UUID REFERENCES account(id)
);

-- Underwriting processors (selection/override per underwriting)
CREATE TABLE underwriting_processors (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES organization(id),
    underwriting_id UUID NOT NULL REFERENCES underwriting(id) ON DELETE CASCADE,
    organization_processor_id UUID REFERENCES organization_processors(id),
    current_executions_list UUID[],
    processor TEXT NOT NULL,
    name TEXT NOT NULL,
    auto BOOLEAN,
    notes TEXT,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    config_override JSONB,
    effective_config JSONB,
    price_snapshot_amount BIGINT,
    price_snapshot_unit TEXT,
    price_snapshot_currency TEXT,
    created_by UUID REFERENCES account(id),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    disabled_at TIMESTAMP,
    disabled_by UUID REFERENCES account(id),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_by UUID REFERENCES account(id),
    UNIQUE (underwriting_id, processor)
);

-- Processor executions (single processor attempt per record)
CREATE TABLE processor_executions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES organization(id),
    underwriting_id UUID NOT NULL REFERENCES underwriting(id) ON DELETE CASCADE,
    organization_processor_id UUID REFERENCES organization_processors(id),
    underwriting_processor_id UUID NOT NULL REFERENCES underwriting_processors(id),
    document_id UUID,
    processor TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('pending', 'running', 'completed', 'failed', 'cancelled')),
    enabled BOOLEAN DEFAULT TRUE,
    factors_delta JSONB,
    payload JSONB,
    payload_hash TEXT,
    run_cost_cents BIGINT,
    currency TEXT NOT NULL DEFAULT 'USD',
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    failed_code TEXT,
    failed_reason TEXT,
    created_by UUID REFERENCES account(id),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    disabled_at TIMESTAMP,
    disabled_by UUID REFERENCES account(id),
    updated_by UUID REFERENCES account(id),
    updated_execution_id UUID REFERENCES processor_executions(id)
);

-- ============================================================================
-- 4) Factors
-- ============================================================================

-- Factor (atomic factors per underwriting)
CREATE TABLE factor (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES organization(id),
    underwriting_id UUID NOT NULL REFERENCES underwriting(id) ON DELETE CASCADE,
    factor_key TEXT NOT NULL,
    value JSONB NOT NULL,
    unit TEXT,
    source TEXT NOT NULL CHECK (source IN ('processor', 'manual')),
    status TEXT NOT NULL CHECK (status IN ('active', 'deleted')),
    factor_hash TEXT,
    underwriting_processor_id UUID REFERENCES underwriting_processors(id),
    execution_id UUID REFERENCES processor_executions(id) ON DELETE SET NULL,
    created_by UUID REFERENCES account(id),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_by UUID REFERENCES account(id),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_factor_id UUID REFERENCES factor(id)
);

-- Factor snapshot
CREATE TABLE factor_snapshot (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES organization(id),
    underwriting_id UUID NOT NULL REFERENCES underwriting(id) ON DELETE CASCADE,
    snapshot_hash TEXT NOT NULL,
    data JSONB NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    created_by UUID NOT NULL REFERENCES account(id),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_by UUID REFERENCES account(id),
    UNIQUE (underwriting_id, snapshot_hash)
);

-- ============================================================================
-- 5) Pre-Check Rules & Evaluations
-- ============================================================================

-- Pre-check rule
CREATE TABLE precheck_rule (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES organization(id),
    name TEXT NOT NULL,
    description TEXT,
    status TEXT NOT NULL CHECK (status IN ('active', 'disabled', 'deleted')),
    criterion JSONB NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    effective_at TIMESTAMP,
    expires_at TIMESTAMP,
    version INT NOT NULL,
    updated_by UUID REFERENCES account(id),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    created_by UUID NOT NULL REFERENCES account(id)
);

-- Pre-check evaluation
CREATE TABLE precheck_evaluation (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES organization(id),
    underwriting_id UUID NOT NULL REFERENCES underwriting(id) ON DELETE CASCADE,
    factor_snapshot_id UUID NOT NULL REFERENCES factor_snapshot(id),
    status TEXT NOT NULL CHECK (status IN ('rejected', 'passed', 'missing')),
    failures JSONB NOT NULL,
    skipped JSONB NOT NULL,
    rule_version INT,
    evaluation_source TEXT CHECK (evaluation_source IN ('processor', 'manual', 'rules_updated')) DEFAULT 'processor',
    evaluation_message_id TEXT,
    evaluated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    created_by UUID REFERENCES account(id),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_by UUID REFERENCES account(id),
    UNIQUE (underwriting_id, factor_snapshot_id)
);

-- ============================================================================
-- 6) Score Card Config & Scores
-- ============================================================================

-- Scorecard config
CREATE TABLE scorecard_config (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES organization(id),
    version INT NOT NULL,
    config JSONB NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    created_by UUID REFERENCES account(id),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_by UUID REFERENCES account(id),
    UNIQUE (organization_id, version)
);

-- Underwriting score
CREATE TABLE underwriting_score (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES organization(id),
    underwriting_id UUID NOT NULL REFERENCES underwriting(id) ON DELETE CASCADE,
    factor_snapshot_id UUID NOT NULL REFERENCES factor_snapshot(id),
    scorecard_version INT NOT NULL,
    score INT NOT NULL CHECK (score BETWEEN 0 AND 100),
    grade TEXT NOT NULL,
    expected_loss NUMERIC(6,3),
    raw_points INT,
    top_reasons JSONB,
    missing_factors JSONB,
    evaluated_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    created_by UUID REFERENCES account(id),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_by UUID REFERENCES account(id),
    UNIQUE (underwriting_id, factor_snapshot_id)
);

-- ============================================================================
-- 7) Suggestions & Decisions
-- ============================================================================

-- Suggestion
CREATE TABLE suggestion (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES organization(id),
    underwriting_id UUID NOT NULL REFERENCES underwriting(id) ON DELETE CASCADE,
    status TEXT NOT NULL CHECK (status IN ('suggested', 'rejected', 'selected')),
    notes TEXT,
    payload JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    created_by UUID REFERENCES account(id),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_by UUID REFERENCES account(id)
);

-- Decision
CREATE TABLE decision (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES organization(id),
    underwriting_id UUID NOT NULL REFERENCES underwriting(id) ON DELETE CASCADE,
    decision TEXT NOT NULL CHECK (decision IN ('approve', 'reject', 'modify')),
    amount_approved NUMERIC(15,2),
    reasoning JSONB,
    funded_amount NUMERIC(15,2),
    payback_amount NUMERIC(15,2),
    terms INT,
    frequency TEXT NOT NULL CHECK (frequency IN ('daily', 'weekly', 'monthly')),
    suggestion_id UUID NOT NULL REFERENCES suggestion(id),
    decision_maker UUID NOT NULL REFERENCES account(id),
    decided_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    created_by UUID REFERENCES account(id),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_by UUID REFERENCES account(id)
);

-- ============================================================================
-- Indexes for performance optimization
-- ============================================================================

-- Underwriting indexes
CREATE INDEX idx_underwriting_organization ON underwriting(organization_id);
CREATE INDEX idx_underwriting_status ON underwriting(status);
CREATE INDEX idx_underwriting_serial ON underwriting(serial_number);

-- Document indexes
CREATE INDEX idx_document_underwriting ON document(underwriting_id);
CREATE INDEX idx_document_organization ON document(organization_id);
CREATE INDEX idx_document_status ON document(status);

-- Processor execution indexes
CREATE INDEX idx_execution_underwriting ON processor_executions(underwriting_id);
CREATE INDEX idx_execution_processor ON processor_executions(processor);
CREATE INDEX idx_execution_status ON processor_executions(status);

-- Factor indexes
CREATE INDEX idx_factor_underwriting ON factor(underwriting_id);
CREATE INDEX idx_factor_key ON factor(factor_key);
CREATE INDEX idx_factor_status ON factor(status);

-- Account indexes
CREATE INDEX idx_account_organization ON account(organization_id);
CREATE INDEX idx_account_email ON account(email);

-- ============================================================================
-- Seed data for testing
-- ============================================================================

-- Insert default roles
INSERT INTO role (name, description) VALUES
    ('SYSTEM_ADMIN', 'System administrator with full access'),
    ('MANAGER', 'Manager with full organizational access'),
    ('UNDERWRITER', 'Underwriter with processing capabilities'),
    ('VIEWER', 'Read-only viewer access');

-- Insert default permissions
INSERT INTO permission (name, description) VALUES
    ('underwriting:read', 'Read underwriting data'),
    ('underwriting:write', 'Create and modify underwritings'),
    ('underwriting:delete', 'Delete underwritings'),
    ('processor:execute', 'Execute processors'),
    ('processor:manage', 'Manage processor configurations'),
    ('rules:read', 'Read business rules'),
    ('rules:manage', 'Manage business rules'),
    ('decision:read', 'Read decisions'),
    ('decision:write', 'Make decisions');

-- Assign permissions to roles
INSERT INTO role_permission (role_id, permission_id)
SELECT r.id, p.id
FROM role r
CROSS JOIN permission p
WHERE r.name = 'SYSTEM_ADMIN';

INSERT INTO role_permission (role_id, permission_id)
SELECT r.id, p.id
FROM role r
CROSS JOIN permission p
WHERE r.name = 'MANAGER' AND p.name IN (
    'underwriting:read', 'underwriting:write', 'underwriting:delete',
    'processor:execute', 'processor:manage', 'rules:read', 'decision:read', 'decision:write'
);

INSERT INTO role_permission (role_id, permission_id)
SELECT r.id, p.id
FROM role r
CROSS JOIN permission p
WHERE r.name = 'UNDERWRITER' AND p.name IN (
    'underwriting:read', 'underwriting:write', 'processor:execute', 'decision:read'
);

INSERT INTO role_permission (role_id, permission_id)
SELECT r.id, p.id
FROM role r
CROSS JOIN permission p
WHERE r.name = 'VIEWER' AND p.name IN (
    'underwriting:read', 'decision:read'
);

-- Insert test organization
INSERT INTO organization (id, name, status) VALUES
    ('00000000-0000-0000-0000-000000000001', 'Test Organization', 'active');

-- Insert test account
INSERT INTO account (id, organization_id, firebase_uid, email, first_name, last_name, status) VALUES
    ('00000000-0000-0000-0000-000000000002', '00000000-0000-0000-0000-000000000001', 'test-firebase-uid', 'test@example.com', 'Test', 'User', 'active');

-- Assign manager role to test account
INSERT INTO account_role (account_id, role_id)
SELECT '00000000-0000-0000-0000-000000000002', id FROM role WHERE name = 'MANAGER';

