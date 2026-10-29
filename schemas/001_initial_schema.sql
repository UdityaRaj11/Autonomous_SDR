-- ============================================================================
-- AUTONOMOUS SDR ENGINE: PRODUCTION DDL SPECIFICATION
-- Target Engine: PostgreSQL 16+
-- Schema: core_engine & audit_compliance
-- Features: UUIDv7, JSONB, GIN indexing, Append-Only Enforced, RLS Multi-Tenancy
-- ============================================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE SCHEMA IF NOT EXISTS core_engine;
CREATE SCHEMA IF NOT EXISTS audit_compliance;

-- ============================================================================
-- ENUM TYPES
-- ============================================================================

CREATE TYPE core_engine.lead_status_enum AS ENUM (
    'PENDING_ENRICHMENT',
    'ENRICHED',
    'SIGNALS_AGGREGATED',
    'PROCESSING_WORKFLOW',
    'AWAITING_HITL_REVIEW',
    'APPROVED',
    'REJECTED',
    'DISPATCHED',
    'FAILED_DEADLETTER',
    'SUPPRESSED_COMPLIANCE'
);

CREATE TYPE core_engine.signal_type_enum AS ENUM (
    'HIRING_EXPANSION',
    'TECH_STACK_MIGRATION',
    'FUNDING_EVENT',
    'LEADERSHIP_APPOINTMENT',
    'REGULATORY_COMPLIANCE_NEED',
    'EARNINGS_CALL_TRANSCRIPT',
    'JOB_POSTING_PAIN_POINT',
    'NEGATIVE_NEWS_RISK'
);

CREATE TYPE core_engine.sentiment_enum AS ENUM (
    'POSITIVE',
    'NEUTRAL',
    'NEGATIVE',
    'HIGH_RISK_NEGATIVE'
);

CREATE TYPE core_engine.workflow_node_enum AS ENUM (
    'NODE1_EXTRACT',
    'NODE2_RANK',
    'NODE3_DRAFT',
    'NODE4_CRITIC'
);

CREATE TYPE core_engine.critic_verdict_enum AS ENUM (
    'PASSED',
    'FLAGGED_WARNING',
    'REJECTED_HALLUCINATION',
    'REJECTED_COMPLIANCE',
    'REJECTED_SPAM_TONE'
);

CREATE TYPE core_engine.hitl_action_enum AS ENUM (
    'APPROVED_UNMODIFIED',
    'APPROVED_WITH_EDITS',
    'REJECTED_BAD_FIT',
    'REJECTED_ACCURACY_ERROR',
    'REASSIGNED_SDR'
);

-- ============================================================================
-- TABLE 1: leads_and_targets
-- Multi-tenant lead and target account registry.
-- ============================================================================

CREATE TABLE core_engine.leads_and_targets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    account_domain VARCHAR(255) NOT NULL,
    company_name VARCHAR(255) NOT NULL,
    lead_first_name VARCHAR(100) NOT NULL,
    lead_last_name VARCHAR(100) NOT NULL,
    lead_title VARCHAR(200) NOT NULL,
    lead_email VARCHAR(255) NOT NULL,
    lead_linkedin_url VARCHAR(500),
    assigned_sdr_id UUID,
    status core_engine.lead_status_enum NOT NULL DEFAULT 'PENDING_ENRICHMENT',
    icp_fit_score NUMERIC(5, 2) CHECK (icp_fit_score >= 0 AND icp_fit_score <= 100),
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
    crypto_shred_key_id VARCHAR(128) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    CONSTRAINT uq_tenant_lead_email UNIQUE (tenant_id, lead_email)
);

CREATE INDEX idx_leads_tenant_status ON core_engine.leads_and_targets (tenant_id, status) WHERE is_deleted = FALSE;
CREATE INDEX idx_leads_assigned_sdr ON core_engine.leads_and_targets (tenant_id, assigned_sdr_id) WHERE is_deleted = FALSE;
CREATE INDEX idx_leads_account_domain ON core_engine.leads_and_targets (tenant_id, account_domain);
CREATE INDEX idx_leads_metadata_gin ON core_engine.leads_and_targets USING GIN (metadata);

-- ============================================================================
-- TABLE 2: signal_records
-- Aggregated intent signals per account and lead.
-- ============================================================================

CREATE TABLE core_engine.signal_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    lead_id UUID NOT NULL REFERENCES core_engine.leads_and_targets(id) ON DELETE CASCADE,
    account_domain VARCHAR(255) NOT NULL,
    signal_type core_engine.signal_type_enum NOT NULL,
    sentiment core_engine.sentiment_enum NOT NULL DEFAULT 'NEUTRAL',
    confidence_score NUMERIC(4, 3) NOT NULL CHECK (confidence_score >= 0.0 AND confidence_score <= 1.0),
    source_name VARCHAR(100) NOT NULL,
    source_uri VARCHAR(1000) NOT NULL,
    raw_payload_hash CHAR(64) NOT NULL,
    raw_payload_s3_uri VARCHAR(1000) NOT NULL,
    dedup_fingerprint CHAR(64) NOT NULL,
    signal_summary TEXT NOT NULL,
    structured_attributes JSONB NOT NULL DEFAULT '{}'::jsonb,
    is_suppressed BOOLEAN NOT NULL DEFAULT FALSE,
    suppression_reason VARCHAR(255),
    detected_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    CONSTRAINT uq_tenant_signal_fingerprint UNIQUE (tenant_id, lead_id, dedup_fingerprint)
);

CREATE INDEX idx_signals_lead ON core_engine.signal_records (tenant_id, lead_id, is_suppressed);
CREATE INDEX idx_signals_domain_detected ON core_engine.signal_records (tenant_id, account_domain, detected_at DESC);
CREATE INDEX idx_signals_type_sentiment ON core_engine.signal_records (tenant_id, signal_type, sentiment);
CREATE INDEX idx_signals_attributes_gin ON core_engine.signal_records USING GIN (structured_attributes);

-- ============================================================================
-- TABLE 3: agent_runs
-- Orchestration traces and execution status for LLM prompt chains.
-- ============================================================================

CREATE TABLE core_engine.agent_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    lead_id UUID NOT NULL REFERENCES core_engine.leads_and_targets(id) ON DELETE RESTRICT,
    temporal_workflow_id VARCHAR(255) NOT NULL,
    temporal_run_id VARCHAR(255) NOT NULL,
    otel_trace_id CHAR(32) NOT NULL,
    active_node core_engine.workflow_node_enum,
    total_prompt_tokens INTEGER NOT NULL DEFAULT 0,
    total_completion_tokens INTEGER NOT NULL DEFAULT 0,
    total_cost_usd NUMERIC(10, 6) NOT NULL DEFAULT 0.000000,
    wall_clock_duration_ms INTEGER NOT NULL DEFAULT 0,
    prompt_bundle_version VARCHAR(50) NOT NULL,
    critic_verdict core_engine.critic_verdict_enum,
    critic_hallucination_score NUMERIC(4, 3) CHECK (critic_hallucination_score >= 0.0 AND critic_hallucination_score <= 1.0),
    critic_spam_score NUMERIC(4, 3) CHECK (critic_spam_score >= 0.0 AND critic_spam_score <= 1.0),
    critic_risk_tags TEXT[] NOT NULL DEFAULT '{}',
    node_outputs JSONB NOT NULL DEFAULT '{}'::jsonb,
    error_details JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    completed_at TIMESTAMPTZ,
    CONSTRAINT uq_workflow_execution UNIQUE (temporal_workflow_id, temporal_run_id)
);

CREATE INDEX idx_agent_runs_lead ON core_engine.agent_runs (tenant_id, lead_id);
CREATE INDEX idx_agent_runs_otel_trace ON core_engine.agent_runs (otel_trace_id);
CREATE INDEX idx_agent_runs_critic_verdict ON core_engine.agent_runs (tenant_id, critic_verdict);
CREATE INDEX idx_agent_runs_created ON core_engine.agent_runs (tenant_id, created_at DESC);

-- ============================================================================
-- TABLE 4: hitl_reviews
-- Human-in-the-Loop review tracking, timing, and edit distances.
-- ============================================================================

CREATE TABLE core_engine.hitl_reviews (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    lead_id UUID NOT NULL REFERENCES core_engine.leads_and_targets(id) ON DELETE RESTRICT,
    agent_run_id UUID NOT NULL REFERENCES core_engine.agent_runs(id) ON DELETE RESTRICT,
    reviewer_user_id UUID NOT NULL,
    action core_engine.hitl_action_enum NOT NULL,
    opened_at TIMESTAMPTZ NOT NULL,
    decided_at TIMESTAMPTZ NOT NULL,
    review_duration_ms INTEGER GENERATED ALWAYS AS (
        CAST(EXTRACT(EPOCH FROM (decided_at - opened_at)) * 1000 AS INTEGER)
    ) STORED,
    original_draft_subject TEXT NOT NULL,
    original_draft_body TEXT NOT NULL,
    final_draft_subject TEXT NOT NULL,
    final_draft_body TEXT NOT NULL,
    subject_levenshtein_distance INTEGER NOT NULL DEFAULT 0,
    body_levenshtein_distance INTEGER NOT NULL DEFAULT 0,
    character_edit_distance_ratio NUMERIC(5, 4) NOT NULL DEFAULT 0.0000,
    feedback_tags TEXT[] NOT NULL DEFAULT '{}',
    rejection_reason_notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);

CREATE INDEX idx_hitl_lead ON core_engine.hitl_reviews (tenant_id, lead_id);
CREATE INDEX idx_hitl_reviewer ON core_engine.hitl_reviews (tenant_id, reviewer_user_id, decided_at DESC);
CREATE INDEX idx_hitl_action ON core_engine.hitl_reviews (tenant_id, action);

-- ============================================================================
-- TABLE 5: audit_trail_events (Partitioned by Month)
-- Immutable cryptographic event log for SOC 2, ISO 27001, GDPR compliance.
-- ============================================================================

CREATE TABLE audit_compliance.audit_trail_events (
    id UUID NOT NULL DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    lead_id UUID NOT NULL,
    agent_run_id UUID,
    event_timestamp TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    event_type VARCHAR(100) NOT NULL,
    actor_type VARCHAR(50) NOT NULL, -- SYSTEM | LLM_NODE | HUMAN_REPRESENTATIVE | EXTERNAL_CONNECTOR
    actor_id VARCHAR(100) NOT NULL,
    otel_trace_id CHAR(32) NOT NULL,
    otel_span_id CHAR(16) NOT NULL,
    payload_hash CHAR(64) NOT NULL,
    previous_event_hash CHAR(64) NOT NULL,
    event_hash CHAR(64) NOT NULL,
    merkle_leaf_index BIGINT,
    worm_archive_s3_uri VARCHAR(1000),
    masked_payload JSONB NOT NULL,
    pii_token_vault_key_id VARCHAR(128),
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    PRIMARY KEY (event_timestamp, id)
) PARTITION BY RANGE (event_timestamp);

-- Default monthly partitions
CREATE TABLE audit_compliance.audit_trail_events_2026_10 PARTITION OF audit_compliance.audit_trail_events
    FOR VALUES FROM ('2026-10-01 00:00:00+00') TO ('2026-11-01 00:00:00+00');

CREATE TABLE audit_compliance.audit_trail_events_2026_11 PARTITION OF audit_compliance.audit_trail_events
    FOR VALUES FROM ('2026-11-01 00:00:00+00') TO ('2026-12-01 00:00:00+00');

CREATE TABLE audit_compliance.audit_trail_events_2026_12 PARTITION OF audit_compliance.audit_trail_events
    FOR VALUES FROM ('2026-12-01 00:00:00+00') TO ('2027-01-01 00:00:00+00');

CREATE INDEX idx_audit_tenant_lead ON audit_compliance.audit_trail_events (tenant_id, lead_id, event_timestamp DESC);
CREATE INDEX idx_audit_trace ON audit_compliance.audit_trail_events (otel_trace_id);
CREATE INDEX idx_audit_event_hash ON audit_compliance.audit_trail_events (event_hash);
CREATE INDEX idx_audit_event_type ON audit_compliance.audit_trail_events (tenant_id, event_type);
CREATE INDEX idx_audit_payload_gin ON audit_compliance.audit_trail_events USING GIN (masked_payload);

-- ============================================================================
-- IMMUTABILITY ENFORCEMENT TRIGGER (Prevents UPDATE and DELETE)
-- ============================================================================

CREATE OR REPLACE FUNCTION audit_compliance.prevent_audit_tampering()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'Audit trail violation: UPDATE and DELETE operations are forbidden on audit_compliance.audit_trail_events.'
    USING ERRCODE = '55000';
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_audit_trail_prevent_update
BEFORE UPDATE ON audit_compliance.audit_trail_events
FOR EACH ROW EXECUTE FUNCTION audit_compliance.prevent_audit_tampering();

CREATE TRIGGER trg_audit_trail_prevent_delete
BEFORE DELETE ON audit_compliance.audit_trail_events
FOR EACH ROW EXECUTE FUNCTION audit_compliance.prevent_audit_tampering();

-- ============================================================================
-- ROW-LEVEL SECURITY (RLS) POLICIES
-- Multi-tenant isolation and role-based access enforcement.
-- ============================================================================

ALTER TABLE core_engine.leads_and_targets ENABLE ROW LEVEL SECURITY;
ALTER TABLE core_engine.signal_records ENABLE ROW LEVEL SECURITY;
ALTER TABLE core_engine.agent_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE core_engine.hitl_reviews ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_compliance.audit_trail_events ENABLE ROW LEVEL SECURITY;

-- Tenant Isolation Policy for Leads
CREATE POLICY tenant_isolation_leads ON core_engine.leads_and_targets
    FOR ALL
    USING (
        tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::UUID
    )
    WITH CHECK (
        tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::UUID
    );

-- SDR Assignment Policy: SDRs can view their assigned leads or unassigned leads in status AWAITING_HITL_REVIEW
CREATE POLICY sdr_assignment_leads ON core_engine.leads_and_targets
    FOR SELECT
    USING (
        tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::UUID
        AND (
            NULLIF(current_setting('app.current_user_role', true), '') IN ('TENANT_ADMIN', 'SALES_MANAGER', 'COMPLIANCE_OFFICER')
            OR assigned_sdr_id = NULLIF(current_setting('app.current_user_id', true), '')::UUID
            OR (assigned_sdr_id IS NULL AND status = 'AWAITING_HITL_REVIEW')
        )
    );

-- Tenant Isolation Policy for Signal Records
CREATE POLICY tenant_isolation_signals ON core_engine.signal_records
    FOR ALL
    USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::UUID)
    WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::UUID);

-- Tenant Isolation Policy for Agent Runs
CREATE POLICY tenant_isolation_agent_runs ON core_engine.agent_runs
    FOR ALL
    USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::UUID)
    WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::UUID);

-- Tenant Isolation Policy for HITL Reviews
CREATE POLICY tenant_isolation_hitl_reviews ON core_engine.hitl_reviews
    FOR ALL
    USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::UUID)
    WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::UUID);

-- Read-Only Policy for Audit Events (Restricted to Compliance Officer and Tenant Admin)
CREATE POLICY audit_events_select_policy ON audit_compliance.audit_trail_events
    FOR SELECT
    USING (
        tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::UUID
        AND NULLIF(current_setting('app.current_user_role', true), '') IN ('TENANT_ADMIN', 'COMPLIANCE_OFFICER', 'AUDITOR')
    );

CREATE POLICY audit_events_insert_policy ON audit_compliance.audit_trail_events
    FOR INSERT
    WITH CHECK (
        tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::UUID
    );
