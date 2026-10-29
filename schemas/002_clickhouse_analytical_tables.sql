-- ============================================================================
-- AUTONOMOUS SDR ENGINE: CLICKHOUSE OLAP READ-MODEL SPECIFICATION
-- Engine: ClickHouse 24+
-- Purpose: Sub-100ms analytical queries for GTM and Compliance Dashboards
-- Data Source: Debezium CDC + Kafka Engine
-- ============================================================================

CREATE DATABASE IF NOT EXISTS sdr_analytics;

-- ============================================================================
-- TABLE 1: hitl_performance_analytics
-- Aggregated daily metrics for SDR review velocity, edit distances, and acceptance rates.
-- ============================================================================

CREATE TABLE IF NOT EXISTS sdr_analytics.hitl_performance_analytics (
    event_date Date,
    tenant_id UUID,
    reviewer_user_id UUID,
    total_reviews UInt32,
    approved_unmodified_count UInt32,
    approved_with_edits_count UInt32,
    rejected_count UInt32,
    total_review_duration_ms UInt64,
    avg_review_duration_ms Float64,
    avg_edit_distance_ratio Float64,
    feedback_tags Array(String)
)
ENGINE = SummingMergeTree()
PARTITION BY toYYYYMM(event_date)
PRIMARY KEY (tenant_id, event_date, reviewer_user_id)
ORDER BY (tenant_id, event_date, reviewer_user_id);

-- ============================================================================
-- TABLE 2: llm_node_telemetry_events
-- Granular telemetry per prompt node for latency, token burn, and critic rejections.
-- ============================================================================

CREATE TABLE IF NOT EXISTS sdr_analytics.llm_node_telemetry_events (
    timestamp DateTime64(3, 'UTC'),
    tenant_id UUID,
    lead_id UUID,
    agent_run_id UUID,
    workflow_node LowCardinality(String),
    model_provider LowCardinality(String),
    model_id LowCardinality(String),
    prompt_bundle_version LowCardinality(String),
    prompt_tokens UInt32,
    completion_tokens UInt32,
    cached_tokens UInt32,
    cost_usd Decimal(10, 6),
    latency_ms UInt32,
    critic_verdict LowCardinality(String),
    hallucination_score Float32,
    spam_score Float32,
    risk_tags Array(String),
    otel_trace_id String
)
ENGINE = MergeTree()
PARTITION BY toYYYYMM(timestamp)
ORDER BY (tenant_id, workflow_node, timestamp, agent_run_id)
SETTINGS index_granularity = 8192;

-- ============================================================================
-- TABLE 3: signal_attribution_and_conversion
-- Tracks conversion downstream (replies, meetings booked, pipeline generated) by signal type.
-- ============================================================================

CREATE TABLE IF NOT EXISTS sdr_analytics.signal_attribution_and_conversion (
    event_date Date,
    tenant_id UUID,
    signal_type LowCardinality(String),
    account_domain String,
    emails_dispatched UInt32,
    emails_opened UInt32,
    replies_received UInt32,
    positive_replies UInt32,
    meetings_booked UInt32,
    pipeline_value_usd Decimal(12, 2)
)
ENGINE = SummingMergeTree()
PARTITION BY toYYYYMM(event_date)
PRIMARY KEY (tenant_id, event_date, signal_type)
ORDER BY (tenant_id, event_date, signal_type, account_domain);
