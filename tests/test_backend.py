"""
Autonomous SDR Engine: Comprehensive Backend Verification Suite
Tests Groq LLM Client, Hybrid RAG, 4-Node Orchestrator, Cryptographic Audit Trail,
Levenshtein Diff Engine, and FastAPI REST Endpoints.
"""

import pytest
import asyncio
from fastapi.testclient import TestClient

from backend.main import app
from backend.llm.groq_client import GroqClientService
from backend.rag.hybrid_retriever import HybridRetriever
from backend.compliance.audit_store import CryptographicAuditStore
from backend.hitl.diff_engine import HITLDiffEngine
from backend.orchestrator.chain import PromptChainOrchestrator
from backend.search.live_search import LiveSearchService

client = TestClient(app)

# -----------------------------------------------------------------------------
# 1. GROQ CLIENT TESTS
# -----------------------------------------------------------------------------
def test_groq_client_initialization_and_cost():
    groq = GroqClientService()
    assert groq is not None
    cost = groq.calculate_cost("llama-3.3-70b-versatile", prompt_tokens=1000, completion_tokens=500)
    assert cost > 0.0

@pytest.mark.asyncio
async def test_groq_client_generation():
    groq = GroqClientService()
    resp = await groq.generate(
        messages=[{"role": "user", "content": "Node 1 extract pain points"}],
        model="llama-3.1-8b-instant",
        json_mode=True
    )
    assert resp.content is not None
    assert resp.prompt_tokens > 0
    assert resp.completion_tokens > 0
    assert resp.duration_ms >= 0

# -----------------------------------------------------------------------------
# 2. HYBRID RAG RETRIEVER TESTS
# -----------------------------------------------------------------------------
def test_hybrid_retriever_rrf():
    retriever = HybridRetriever()
    results = retriever.retrieve("SOC 2 audit continuous telemetry EKS", top_k=2)
    assert len(results) == 2
    assert results[0].final_rank == 1
    assert results[0].dense_score > 0.0
    assert results[0].bm25_score >= 0.0
    assert results[0].rrf_score > 0.0

# -----------------------------------------------------------------------------
# 3. CRYPTOGRAPHIC AUDIT STORE & TAMPER-PROOFING TESTS
# -----------------------------------------------------------------------------
def test_audit_store_hash_chain_and_tamper_detection():
    store = CryptographicAuditStore(tenant_id="test-tenant")
    
    # Record Event 1
    e1 = store.record_event(
        lead_id="lead-1",
        event_type="SIGNAL_SCRAPED",
        actor_type="SYSTEM_SERVICE",
        actor_id="worker-1",
        trace_id="trace-1",
        raw_payload={"test": "data 1", "email": "test@example.com"}
    )
    assert e1.cryptographic_integrity.previous_event_sha256 == "0" * 64
    assert e1.data_privacy.pii_masked is True
    assert "{{TOKEN_LEAD_EMAIL}}" in str(e1.payload)

    # Record Event 2
    e2 = store.record_event(
        lead_id="lead-1",
        event_type="NODE3_DRAFT_EXECUTED",
        actor_type="LLM_CHAIN_WORKER",
        actor_id="groq-worker",
        trace_id="trace-1",
        raw_payload={"draft": "hello"}
    )
    assert e2.cryptographic_integrity.previous_event_sha256 == e1.cryptographic_integrity.event_sha256

    # Verify chain integrity
    verification = store.verify_chain_integrity()
    assert verification["verified"] is True
    assert verification["status"] == "VALID_AND_TAMPER_FREE"

    # Simulate malicious in-place tampering with event 1 payload
    store.events[1].payload["malicious_field"] = "hacked"
    tampered_verification = store.verify_chain_integrity()
    assert tampered_verification["verified"] is False
    assert "Payload hash mismatch" in tampered_verification["reason"]

# -----------------------------------------------------------------------------
# 4. LEVENSHTEIN & HITL DIFF ENGINE TESTS
# -----------------------------------------------------------------------------
def test_hitl_diff_engine():
    orig = "Hello world from the outreach agent."
    final = "Hello world from the modified sales agent."
    
    metrics = HITLDiffEngine.compute_metrics(
        orig_subject="Quick question",
        final_subject="Quick question",
        orig_body=orig,
        final_body=final
    )
    assert metrics.body_levenshtein_distance > 0
    assert metrics.character_edit_distance_ratio > 0.0
    assert metrics.is_modified is True

    # Test identical strings
    identical_metrics = HITLDiffEngine.compute_metrics("Subj", "Subj", orig, orig)
    assert identical_metrics.body_levenshtein_distance == 0
    assert identical_metrics.character_edit_distance_ratio == 0.0
    assert identical_metrics.is_modified is False

# -----------------------------------------------------------------------------
# 5. 4-NODE CHAIN ORCHESTRATION TESTS
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_orchestrator_4_node_execution():
    orchestrator = PromptChainOrchestrator()
    res = await orchestrator.execute_chain(
        lead_id="test-lead-123",
        lead_name="Julian Vance",
        company_name="NeoPay",
        title="VP Platform",
        email="julian@neopay.eu",
        domain="neopay.eu",
        trace_id="test-trace-12345"
    )
    assert res.workflow_status == "AWAITING_HITL_REVIEW"
    assert res.total_tokens > 0
    assert "node" in res.node1_extract
    assert "node" in res.node2_rank
    assert "node" in res.node3_draft
    assert "node" in res.node4_critic
    assert res.node4_critic["critic_results"]["verdict"] in ["PASSED", "FLAGGED_WARNING"]

# -----------------------------------------------------------------------------
# 6. FASTAPI ENDPOINT TESTS
# -----------------------------------------------------------------------------
def test_api_health_endpoint():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "HEALTHY"
    assert data["llm_provider"] == "Groq"
    assert data["audit_chain_integrity"] is True

def test_api_leads_endpoint():
    response = client.get("/api/v1/leads")
    assert response.status_code == 200
    assert "leads" in response.json()
    assert len(response.json()["leads"]) > 0

def test_api_pipeline_execute():
    payload = {
        "lead_name": "Sarah Chen",
        "company_name": "CloudScale AI",
        "title": "Head of Infra",
        "email": "sarah@cloudscale.ai",
        "account_domain": "cloudscale.ai",
        "force_live_search": True
    }
    response = client.post("/api/v1/pipeline/execute", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "trace_id" in data
    assert data["workflow_status"] == "AWAITING_HITL_REVIEW"
    assert "node3_draft" in data["nodes"]
    assert "live_signals" in data
    assert len(data["live_signals"]) > 0
    assert "search_metadata" in data
    assert "payload_sha256" in data["search_metadata"]

def test_api_hitl_submit():
    payload = {
        "lead_id": "test-lead-1",
        "trace_id": "test-trace-1",
        "reviewer_id": "sdr-user-sarah",
        "action": "APPROVED_WITH_EDITS",
        "original_subject": "Test Subj",
        "final_subject": "Test Subj Edited",
        "original_body": "Original email content.",
        "final_body": "Original email content with some edits.",
        "feedback_tags": ["STRONGER_HOOK"],
        "review_duration_seconds": 25
    }
    response = client.post("/api/v1/hitl/submit", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "RECORDED"
    assert data["levenshtein_distance"] > 0
    assert data["is_modified"] is True

def test_api_audit_events():
    response = client.get("/api/v1/audit/events")
    assert response.status_code == 200
    data = response.json()
    assert "events" in data
    assert data["chain_integrity"]["verified"] is True

def test_api_groq_models():
    response = client.get("/api/v1/groq/models")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "SUCCESS"
    assert "resolved_quality_model" in data
    assert "resolved_fast_model" in data

@pytest.mark.asyncio
async def test_live_search_service():
    service = LiveSearchService()
    res = await service.search_company_signals(
        company_name="CloudScale AI",
        person_name="Sarah Chen",
        title="Head of Infra",
        domain="cloudscale.ai"
    )
    assert res is not None
    assert "signals" in res
    assert len(res["signals"]) > 0
    assert "payload_sha256" in res
    assert len(res["payload_sha256"]) == 64

def test_api_live_search():
    payload = {
        "company_name": "CloudScale AI",
        "person_name": "Sarah Chen",
        "title": "Head of Infra",
        "domain": "cloudscale.ai"
    }
    response = client.post("/api/v1/search/live", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "signals" in data
    assert len(data["signals"]) > 0
    assert data["company_name"] == "CloudScale AI"

def test_pipeline_zero_signals_circuit_breaker():
    payload = {
        "lead_id": "test-circuit-breaker-fictional",
        "company_name": "jamsesbond",
        "lead_name": "Uditya Raj",
        "title": "Director of Enterprise AI Solutions",
        "email": "u.raj@jamsesbond.com",
        "account_domain": "jamsesbond.com",
        "force_live_search": True
    }
    response = client.post("/api/v1/pipeline/execute", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["workflow_status"] == "REJECTED_ZERO_SIGNALS"
    assert len(data["live_signals"]) == 0
    assert data["total_tokens"] == 0
    assert data["nodes"]["node2_rank"]["ranked_data"]["icp_fit_score"] == 0.0
    assert "[BLOCKED]" in data["nodes"]["node3_draft"]["draft_output"]["subject"]
    assert data["nodes"]["node4_critic"]["critic_results"]["verdict"] == "REJECTED_ZERO_SIGNALS"



