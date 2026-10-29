"""
Unit & Integration Tests for Live Dashboard Analytics and Real-Time Telemetry
"""

import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.db.database import DatabaseManager

client = TestClient(app)

def test_dashboard_metrics_schema_and_types():
    resp = client.get("/api/v1/dashboard/metrics")
    assert resp.status_code == 200
    data = resp.json()

    # Verify KPI fields
    assert "pipeline_generated_usd" in data
    assert "draft_approval_rate_percent" in data
    assert "approval_clean_percent" in data
    assert "approval_edited_percent" in data
    assert "avg_review_duration_seconds" in data
    assert "mean_edit_distance_ratio_percent" in data
    assert "total_token_burn_cost_usd" in data
    assert "total_tokens_consumed" in data
    assert "critic_rejection_rate_percent" in data
    assert "critic_suppressed_count" in data
    assert "total_reviews_count" in data
    assert "active_leads_count" in data

    assert isinstance(data["pipeline_generated_usd"], (int, float))
    assert data["pipeline_generated_usd"] > 0
    assert 0 <= data["draft_approval_rate_percent"] <= 100

    # Verify Chart objects
    assert "charts" in data
    charts = data["charts"]
    
    # 1. Throughput Chart
    assert "throughput" in charts
    assert len(charts["throughput"]["labels"]) == 7
    assert len(charts["throughput"]["approved_clean"]) == 7
    assert len(charts["throughput"]["approved_with_edits"]) == 7
    assert len(charts["throughput"]["rejected"]) == 7

    # 2. Signals Chart
    assert "signals" in charts
    assert len(charts["signals"]["labels"]) >= 3
    assert len(charts["signals"]["dispatched_count"]) == len(charts["signals"]["labels"])

    # 3. Hallucination Distribution Chart
    assert "hallucination" in charts
    assert len(charts["hallucination"]["labels"]) == 6
    assert len(charts["hallucination"]["draft_counts"]) == 6

    # 4. SDR Reps Chart
    assert "reps" in charts
    assert len(charts["reps"]["labels"]) >= 3
    assert len(charts["reps"]["avg_duration_sec"]) == len(charts["reps"]["labels"])

def test_dashboard_dynamic_increment_on_review():
    # 1. Fetch initial metrics
    resp_init = client.get("/api/v1/dashboard/metrics")
    assert resp_init.status_code == 200
    init_data = resp_init.json()
    init_pipeline = init_data["pipeline_generated_usd"]
    init_reviews = init_data["total_reviews_count"]

    # 2. Submit a new HITL review (Clean Approval)
    review_payload = {
        "lead_id": "lead-neo-01",
        "trace_id": "test-dynamic-trace-123",
        "reviewer_id": "sdr-user-sarah",
        "action": "APPROVED_CLEAN",
        "original_subject": "Initial test subject",
        "original_body": "Initial test body",
        "final_subject": "Initial test subject",
        "final_body": "Initial test body",
        "feedback_tags": ["tested_dynamic_update"],
        "review_duration_seconds": 25
    }
    sub_resp = client.post("/api/v1/hitl/submit", json=review_payload)
    assert sub_resp.status_code == 200

    # 3. Fetch updated metrics and verify dynamic calculation
    resp_updated = client.get("/api/v1/dashboard/metrics")
    assert resp_updated.status_code == 200
    updated_data = resp_updated.json()

    assert updated_data["total_reviews_count"] == init_reviews + 1
    assert updated_data["pipeline_generated_usd"] == init_pipeline + 25000.0

def test_audit_events_endpoint_and_chain_integrity():
    resp = client.get("/api/v1/audit/events?limit=50")
    assert resp.status_code == 200
    data = resp.json()

    assert "chain_integrity" in data
    assert data["chain_integrity"]["verified"] is True
    assert data["chain_integrity"]["status"] == "VALID_AND_TAMPER_FREE"
    assert len(data["events"]) >= 10
    
    # Verify canonical event structure
    first_event = data["events"][0]
    assert "event_id" in first_event
    assert "cryptographic_integrity" in first_event
    assert "event_sha256" in first_event["cryptographic_integrity"]
    assert "previous_event_sha256" in first_event["cryptographic_integrity"]
    assert "worm_storage_uri" in first_event["cryptographic_integrity"]
    assert "payload" in first_event
    assert "company_name" in first_event

def test_dashboard_approved_unmodified_increments_clean():
    # 1. Fetch initial metrics
    resp_init = client.get("/api/v1/dashboard/metrics")
    assert resp_init.status_code == 200
    init_data = resp_init.json()
    init_pipeline = init_data["pipeline_generated_usd"]
    init_reviews = init_data["total_reviews_count"]
    init_today_clean = init_data["charts"]["throughput"]["approved_clean"][-1]

    # 2. Submit APPROVED_UNMODIFIED review (action from frontend button)
    review_payload = {
        "lead_id": "lead-tred-02",
        "trace_id": "test-unmodified-trace-999",
        "reviewer_id": "sdr-user-5541",
        "action": "APPROVED_UNMODIFIED",
        "original_subject": "Automating evidence collection",
        "original_body": "Noticed Tredence is scaling platform operations.",
        "final_subject": "Automating evidence collection",
        "final_body": "Noticed Tredence is scaling platform operations.",
        "feedback_tags": [],
        "review_duration_seconds": 18
    }
    sub_resp = client.post("/api/v1/hitl/submit", json=review_payload)
    assert sub_resp.status_code == 200

    # 3. Verify metrics increment
    resp_updated = client.get("/api/v1/dashboard/metrics")
    assert resp_updated.status_code == 200
    updated_data = resp_updated.json()

    assert updated_data["total_reviews_count"] == init_reviews + 1
    assert updated_data["pipeline_generated_usd"] == init_pipeline + 25000.0
    assert updated_data["charts"]["throughput"]["approved_clean"][-1] == init_today_clean + 1

def test_anti_cache_headers_present():
    resp1 = client.get("/api/v1/dashboard/metrics")
    assert "no-cache" in resp1.headers.get("cache-control", "")
    assert "no-store" in resp1.headers.get("cache-control", "")

    resp2 = client.get("/api/v1/audit/events")
    assert "no-cache" in resp2.headers.get("cache-control", "")
    assert "no-store" in resp2.headers.get("cache-control", "")
