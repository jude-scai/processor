## 1) Identity, Tenancy, Auth & RBAC

### organization

```sql
id UUID PRIMARY KEY,
name TEXT NOT NULL,
status TEXT NOT NULL CHECK (status IN ('active','suspended', 'deleted')), // default 'active'
created_at TIMESTAMP NOT NULL,
updated_at TIMESTAMP NOT NULL

```

### account (user)

```sql
id UUID PRIMARY KEY,
organization_id UUID NOT NULL REFERENCES organization(id),
firebase_uid TEXT NOT NULL UNIQUE,        -- Firebase Auth user id
email TEXT NOT NULL,
first_name TEXT NULL,
last_name TEXT NULL,
status TEXT NOT NULL CHECK (status IN ('active','invited','disabled')), -- default 'active' user can change it later on
created_at TIMESTAMP NOT NULL,
updated_at TIMESTAMP NOT NULL,
UNIQUE (organization_id, email)

```

### role (seed: MANAGER, UNDERWRITER, VIEWER)

```sql
id UUID PRIMARY KEY,
name TEXT NOT NULL UNIQUE,            -- 'SYSTEM ADMIN' | 'MANAGER'|'UNDERWRITER'|'VIEWER'
description TEXT,
created_at TIMESTAMP NOT NULL,
updated_at TIMESTAMP NOT NULL

```

### permission (granular capability catalog)

```sql
id UUID PRIMARY KEY,
name TEXT NOT NULL UNIQUE,            -- e.g., 'underwriting:write', 'rules:manage'
description TEXT

```

### role_permission (assign permissions to roles)

```sql
role_id UUID NOT NULL REFERENCES role(id),
permission_id UUID NOT NULL REFERENCES permission(id),
PRIMARY KEY (role_id, permission_id)

```

### account_role (assign roles to accounts)

```sql
account_id UUID NOT NULL REFERENCES account(id),
role_id UUID NOT NULL REFERENCES role(id),
PRIMARY KEY (account_id, role_id)

```

-- Password reset and email verification are handled by Firebase; no local tables required.

### organization_invitation (invite-based onboarding)

```sql
id UUID PRIMARY KEY,
organization_id UUID NOT NULL REFERENCES organization(id),
email TEXT NOT NULL,
role_name TEXT NOT NULL CHECK (role_name IN ('MANAGER','UNDERWRITER','VIEWER')),
token_hash TEXT NOT NULL,
status TEXT NOT NULL CHECK (status IN ('pending','accepted','expired')),
invited_by UUID NOT NULL REFERENCES account(id),
expires_at TIMESTAMP NOT NULL,
accepted_at TIMESTAMP,
account_id UUID NULL REFERENCES account(id),
created_at TIMESTAMP NOT NULL

```

### idempotency_key (request-level)

```sql
organization_id UUID NOT NULL REFERENCES organization(id),
scope TEXT NOT NULL,
key TEXT NOT NULL,
response_hash TEXT,
created_at TIMESTAMP NOT NULL,
PRIMARY KEY (organization_id, scope, key)

```

---

## 2) Core Underwriting & Application Data

### underwriting (root aggregate)

```sql
id UUID PRIMARY KEY,
organization_id UUID NOT NULL REFERENCES organization(id),
serial_number TEXT NOT NULL -- in a specific format (A-MMDDYY-234) and will increase automatically
status TEXT NOT NULL CHECK (status IN ('created','processing','rejected','missing','passed','suggested','decided', 'cancelled', 'deleted')),
application_type TEXT CHECK (application_type IN ('NEW','RENEWAL')),
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
created_at TIMESTAMP NOT NULL,
updated_at TIMESTAMP NOT NULL,
created_by UUID NOT NULL REFERENCES account(id),
updated_by UUID NOT NULL REFERENCES account(id),

```

### merchant_address

```sql
id UUID PRIMARY KEY,
underwriting_id UUID NOT NULL REFERENCES underwriting(id) ON DELETE CASCADE,
addr_1 TEXT,
addr_2 TEXT,
city TEXT,
state TEXT,
zip TEXT,
created_at TIMESTAMP NOT NULL,
updated_at TIMESTAMP NOT NULL,
created_by UUID NOT NULL REFERENCES account(id),
updated_by UUID NOT NULL REFERENCES account(id),

```

### owner (beneficial owners)

```sql
id UUID PRIMARY KEY,
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
enabled bool NOT NULL TRUE -- Use this to mark it as deleted or not
ownership_percent NUMERIC(5,2),
primary_owner BOOLEAN DEFAULT FALSE,
created_at TIMESTAMP NOT NULL,
updated_at TIMESTAMP NOT NULL,
created_by UUID NOT NULL REFERENCES account(id),
updated_by UUID NOT NULL REFERENCES account(id),

```

### owner_address

```sql
id UUID PRIMARY KEY,
owner_id UUID NOT NULL REFERENCES owner(id) ON DELETE CASCADE,
addr_1 TEXT,
addr_2 TEXT,
city TEXT,
state TEXT,
zip TEXT,
created_at TIMESTAMP NOT NULL,
updated_at TIMESTAMP NOT NULL,
created_by UUID NOT NULL REFERENCES account(id),
updated_by UUID NOT NULL REFERENCES account(id),

```

### document (artifact pointer + classification)

```sql
id UUID PRIMARY KEY,
organization_id UUID NOT NULL REFERENCES organization(id),
underwriting_id UUID NOT NULL REFERENCES underwriting(id) ON DELETE CASCADE,
status TEXT NOT NULL CHECK (status IN ('uploaded','accepted','rejected','deleted')),
current_revision_id UUID NULL,
stipulation_type TEXT NULL,
classification_confidence NUMERIC(5,2) NULL,
created_at TIMESTAMP NOT NULL,
created_by UUID NOT NULL REFERENCES account(id),
updated_at TIMESTAMP NOT NULL,
updated_by UUID NULL REFERENCES account(id),
```

### document_revision (upload/replace history)

```sql
id UUID PRIMARY KEY,
document_id UUID NOT NULL REFERENCES document(id) ON DELETE CASCADE,
gcs_uri TEXT NOT NULL,
ocr_gcs_uri TEXT NULL,
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
created_at TIMESTAMP NOT NULL,
created_by UUID NULL REFERENCES account(id),
updated_at TIMESTAMP NOT NULL,
updated_by UUID NULL REFERENCES account(id),
UNIQUE (document_id, revision)
```

---

## 3) Processing, Catalog, Executions, Costs

-- Processor catalog is code-managed (JSON in codebase). No DB table for processors.

### organization_processors(entitlements; organization or underwriting scoped)

```sql
id UUID PRIMARY KEY,
organization_id UUID NOT NULL REFERENCES organization(id),
processor TEXT NOT NULL,
name TEXT NOT NULL,
auto bool NOT NULL TRUE,
price_amount BIGINT,                                     -- cents price at purchase time (immutable)
price_unit TEXT,                                         -- unit (document, page, execution)
price_currency TEXT NOT NULL DEFAULT 'USD',
purchased_by UUID NOT NULL REFERENCES account(id),
purchased_at TIMESTAMP NOT NULL,
status TEXT NOT NULL CHECK (status IN ('active','disabled','deleted')),
config JSONB,                                            -- config snapshot at purchase
notes TEXT,
created_at TIMESTAMP NOT NULL,
created_by UUID NULL REFERENCES account(id),
disabled_at TIMESTAMP NULL,
disabled_by UUID NULL REFERENCES account(id),
updated_at TIMESTAMP NOT NULL
updated_by UUID NULL REFERENCES account(id),
```

-- Unifies organization-level and underwriting-level purchases with `scope`.

-- For underwriting-scoped purchases, set `scope='underwriting'` and `underwriting_id`.

### underwriting_processors (selection/override per underwriting)

```sql
id UUID PRIMARY KEY,
organization_id UUID NOT NULL REFERENCES organization(id),
underwriting_id UUID NOT NULL REFERENCES underwriting(id) ON DELETE CASCADE,
organization_processor_id UUID NULL REFERENCES organization_processors(id),
current_executions_list ARRAY NULL
processor TEXT NOT NULL,
name TEXT NOT NULL,
auto BOOL NULL,                                        -- enable automatic execution for this underwriting
notes TEXT,
enabled Bool NOT NULL TRUE,
config_override JSONB,                                 -- overrides on top of purchase config
effective_config JSONB,                                -- resolved config at selection time (purchase.config + overrides)
price_snapshot_amount BIGINT,                          -- optional price snapshot for this underwriting
price_snapshot_unit TEXT,
price_snapshot_currency TEXT,
created_by UUID NULL REFERENCES account(id),
created_at TIMESTAMP NOT NULL,
disabled_at TIMESTAMP NULL,
disabled_by UUID NULL REFERENCES account(id),
updated_at NOT NULL TIMESTAMP,
updated_by UUID NULL REFERENCES account(id),
UNIQUE (underwriting_id, processor_key)
```

-- This table lists processors enabled for a specific underwriting.

-- It may reference a organization-level entitlement or an underwriting-scoped purchase.

### processor_executions (single processor attempt per record)

```sql
id UUID PRIMARY KEY,
organization_id UUID NOT NULL REFERENCES organization(id),
underwriting_id UUID NOT NULL REFERENCES underwriting(id) ON DELETE CASCADE,
organization_processor_id UUID NULL REFERENCES organization_processors(id),
underwriting_processor_id UUID NOT NULL REFERENCES underwriting_processor(id),
--document_list document_revision(id)[] NULL combined to payload -- storing list of id's of all the documents against which the current execution made
document_id TEXT NULL --  This is for current execution of document based processor
processor TEXT NOT NULL,             -- current_exeution_list is determined based on this processor not on stipulation type
status TEXT NOT NULL CHECK (status IN ('pending','running','completed','failed','cancelled')),
enabled bool  -- If this execution is in the list of current_executions_list then mark it as enabled
factors_delta JSONB,                     -- factors written by this execution
payload JSONB,                           -- only the triggers
payload_hash TEXT,                       -- hash for triggered payload
run_cost_cents BIGINT,                   -- cost in cents at run time
currency TEXT NOT NULL DEFAULT 'USD',
started_at TIMESTAMP,
completed_at TIMESTAMP,
failed_code TEXT NULL,
failed_reason TEXT NULL,
created_by UUID NULL REFERENCES account(id),
created_at TIMESTAMP NOT NULL,
updated_at TIMESTAMP NOT NULL,
disabled_at TIMESTAMP NULL,
disabled_by UUID NULL REFERENCES account(id),
updated_by UUID NULL REFERENCES account(id),
updated_execution_id UUID NULL REFERENCES processor_execution(id) -- saving most up to date execution against the documents
```

## 4) Factors

### factor (atomic factors per underwriting)

```sql
id UUID PRIMARY KEY,
organization_id UUID NOT NULL REFERENCES organization(id),
underwriting_id UUID NOT NULL REFERENCES underwriting(id) ON DELETE CASCADE,
factor_key TEXT NOT NULL,                 -- e.g., 'f.avg_revenue', 'owners[0].credit_score.score'
value JSONB NOT NULL,                    -- typed value; store as JSONB to support number/string/bool/array
unit TEXT,                                -- optional units (e.g., 'USD/month')
source TEXT NOT NULL CHECK (source IN ('processor','manual')),
status TEXT NOT NULL CHECK (status IN ('active','deleted')),
factor_hash TEXT,  -- computed hash from factor_key + value + source
underwriting_processor_id UUID NULL REFERENCES underwriting_processor(id),
execution_id UUID NULL REFERENCES processor_execution(id) ON DELETE SET NULL,
--document_revision_id UUID NULL REFERENCES document_revision(id) ON DELETE SET NULL, # Question:
created_by UUID NULL REFERENCES account(id),
created_at TIMESTAMP NOT NULL,
updated_by UUID NULL REFERENCES account(id),
updated_at TIMESTAMP NOT NULL,
updated_factor_id UUID NULL REFERENCES factor(id) -- save id of the most up to date factor against the factor key
```

Notes:

- Each processor execution can write multiple factor rows; link them via `execution_id` (one-to-many).
- Manual factor entries use `source = 'manual'` with `created_by` populated; `underwriting_processor_id` and `execution_id` remains NULL.

### factor_snapshot

```sql
id UUID PRIMARY KEY,
organization_id UUID NOT NULL REFERENCES organization(id),
underwriting_id UUID NOT NULL REFERENCES underwriting(id) ON DELETE CASCADE,
snapshot_hash TEXT NOT NULL,
data JSONB NOT NULL,
created_at TIMESTAMP NOT NULL,
created_by UUID NOT NULL REFERENCES account(id),
updated_at TIMESTAMP NOT NULL,
updated_by UUID NULL REFERENCES account(id),
UNIQUE (underwriting_id, snapshot_hash)

```

Snapshot guidance:

- **Maintain only single factor snapshot per underwriting. In case of new factor snapshot just replace previous one we will not store the history**
- `factor_snapshot.data` is a materialized, merged view of all `factor` rows
- Compute `snapshot_hash` from the canonicalized `data`. Use snapshots for Pre‑Check/Score Card idempotency and audit.

---

## 5) Pre-Check Rules & Evaluations

### precheck_rule (versioned per row or via separate versions table)

```sql
id UUID PRIMARY KEY,                                             -- unique identifier for each rule
organization_id UUID NOT NULL REFERENCES organization(id),       -- rule belongs to a specific organization
name TEXT NOT NULL,                                              -- human-readable name (e.g. "Minimum Revenue Requirement")
description TEXT,                                                -- optional longer explanation or policy reference
status TEXT NOT NULL CHECK (status IN ('active','disabled', 'deleted')),
criterion JSONB NOT NULL,                                        -- rule definition (factors, operators, and values in JSON form)
created_at TIMESTAMP NOT NULL DEFAULT now(),                     -- creation timestamp
effective_at TIMESTAMP,                                          -- optional start date when rule becomes effective
expires_at TIMESTAMP,                                            -- optional end date for rule validity
version INT NOT NULL,                                            -- version number (incremented on updates)
updated_by UUID REFERENCES account(id),                          -- user/account who last updated the rule
updated_at TIMESTAMP NOT NULL                                    -- timestamp of last modification
created_by TIMESTAMP NOT NULL,
```

### precheck_evaluation

```sql
id UUID PRIMARY KEY,                                                -- unique identifier for this evaluation record
organization_id UUID NOT NULL REFERENCES organization(id),          -- organization that owns this underwriting
underwriting_id UUID NOT NULL REFERENCES underwriting(id) ON DELETE CASCADE,  -- underwriting being evaluated; cascade delete when underwriting is removed
factor_snapshot_id UUID NOT NULL REFERENCES factor_snapshot(id),    -- snapshot of factors used for this evaluation (immutable input)

status TEXT NOT NULL CHECK (status IN ('rejected','passed','missing')),  -- overall evaluation result
failures JSONB NOT NULL,                                            -- list of failed rules with messages and criteria snapshots
skipped JSONB NOT NULL,                                             -- list of rules skipped due to missing factors or data gaps

rule_version INT,                                                  -- label, tag, or hash of rule set used for evaluation
evaluation_source TEXT CHECK (evaluation_source IN ('processor','manual','rules_updated')) DEFAULT 'processor',
                                                                        -- indicates what triggered the evaluation (system or user action)
evaluation_message_id TEXT,                                         -- Pub/Sub message ID for traceability and idempotent processing
evaluated_at TIMESTAMP NOT NULL DEFAULT now(),                      -- timestamp of when evaluation completed
created_by UUID NULL REFERENCES account(id),
updated_at TIMESTAMP NOT NULL,
updated_by UUID NULL REFERENCES account(id),
UNIQUE (underwriting_id, factor_snapshot_id)                        -- ensures one evaluation per underwriting per snapshot (idempotency)
```

---

## 6) Score Card Config & Scores

### scorecard_config

```sql
id UUID PRIMARY KEY,
organization_id UUID NOT NULL REFERENCES organization(id),
version INT NOT NULL,                 -- immutable label
config JSONB NOT NULL,                 -- bins, weights, grading, reasons
created_at TIMESTAMP NOT NULL,
created_by UUID REFERENCES account(id),
updated_at TIMESTAMP NOT NULL,
updated_by UUID NULL REFERENCES account(id),
UNIQUE (organization_id, version)

```

### underwriting_score

```sql
id UUID PRIMARY KEY,
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
created_at TIMESTAMP NOT NULL,
created_by UUID NULL REFERENCES account(id),
updated_at TIMESTAMP NOT NULL,
updated_by UUID NULL REFERENCES account(id),
UNIQUE (underwriting_id, factor_snapshot_id)

```

---

## 7) Suggestions & Decisions

### suggestion

```sql
id UUID PRIMARY KEY,
organization_id UUID NOT NULL REFERENCES organization(id),
underwriting_id UUID NOT NULL REFERENCES underwriting(id) ON DELETE CASCADE,
status TEXT NOT NULL CHECK (status IN ('suggested','rejected','selected')),
notes TEXT NULL,
payload JSONB,                          -- generated suggestions
created_at TIMESTAMP NOT NULL,
created_by UUID NULL REFERENCES account(id),
updated_at TIMESTAMP NOT NULL,
updated_by UUID NULL REFERENCES account(id),

```

### decision

```sql
id UUID PRIMARY KEY,
organization_id UUID NOT NULL REFERENCES organization(id),
underwriting_id UUID NOT NULL REFERENCES underwriting(id) ON DELETE CASCADE,
decision TEXT NOT NULL CHECK (decision IN ('approve','reject','modify')),
amount_approved NUMERIC(15,2),
reasoning JSONB,
funded_amount NUMERIC(15,2),
payback_amount NUMERIC(15,2),
terms INT -- IN Months 1= 1 Month, 0.5 = 2 weeks
frequency TEXT NOT NULL CHECK (frequency IN ('daily','weekly','monthly')), # daily, weekly or monthly
suggestion_id UUID NOT NULL REFERENCES suggestion(id)
decision_maker UUID NOT NULL REFERENCES account(id),
decided_at TIMESTAMP NOT NULL
created_at TIMESTAMP NOT NULL,
created_by UUID NULL REFERENCES account(id),
updated_at TIMESTAMP NOT NULL,
updated_by UUID NULL REFERENCES account(id),
```
