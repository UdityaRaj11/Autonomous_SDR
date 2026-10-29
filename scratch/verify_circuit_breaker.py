import sys
import requests
import json

# Ensure stdout handles UTF-8 on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE_URL = "http://127.0.0.1:8000"

def test_jamsesbond_zero_signal_guardrail():
    print("--- TEST 1: Fictional Entity 'jamsesbond' ---")
    payload = {
        "lead_id": "test-jamsesbond-uuid-999",
        "lead_name": "Uditya Raj",
        "company_name": "jamsesbond",
        "title": "Director of Enterprise AI Solutions",
        "email": "u.raj@jamsesbond.com",
        "account_domain": "jamsesbond.com",
        "focus_query": "AI platform scaling, SOC 2",
        "force_live_search": True
    }
    
    resp = requests.post(f"{BASE_URL}/api/v1/pipeline/execute", json=payload, timeout=20)
    print(f"Status Code: {resp.status_code}")
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    data = resp.json()
    
    print(f"Workflow Status: {data.get('workflow_status')}")
    assert data.get("workflow_status") == "REJECTED_ZERO_SIGNALS", f"Expected REJECTED_ZERO_SIGNALS, got {data.get('workflow_status')}"
    
    live_signals = data.get("live_signals", [])
    print(f"Live Signals Count: {len(live_signals)}")
    assert len(live_signals) == 0, f"Expected 0 live signals, got {len(live_signals)}"
    
    n2 = data["nodes"]["node2_rank"]
    icp_score = n2["ranked_data"]["icp_fit_score"]
    print(f"Node 2 ICP Fit Score: {icp_score}")
    assert icp_score == 0.0, f"Expected 0.0 ICP score, got {icp_score}"
    
    n3 = data["nodes"]["node3_draft"]
    subject = n3["draft_output"]["subject"]
    print(f"Node 3 Subject: {subject}")
    assert "[BLOCKED]" in subject, f"Expected [BLOCKED] in subject, got {subject}"
    
    n4 = data["nodes"]["node4_critic"]
    verdict = n4["critic_results"]["verdict"]
    hallucination_score = n4["critic_results"]["hallucination_score"]
    print(f"Node 4 Critic Verdict: {verdict}, Hallucination Score: {hallucination_score}")
    assert verdict == "REJECTED_ZERO_SIGNALS"
    assert hallucination_score == 1.0
    
    print(f"Tokens consumed: {data.get('total_tokens')}")
    assert data.get("total_tokens") == 0, f"Expected 0 tokens burned, got {data.get('total_tokens')}"
    
    print("Testing dispatch guardrail for blocked lead...")
    hitl_payload = {
        "lead_id": "test-jamsesbond-uuid-999",
        "reviewer_id": "rep_sarah_01",
        "action": "APPROVE_AND_DISPATCH",
        "review_duration_seconds": 12,
        "original_subject": subject,
        "final_subject": subject,
        "original_body": n3["draft_output"]["body"],
        "final_body": n3["draft_output"]["body"],
        "feedback_tags": [],
        "rejection_notes": None,
        "trace_id": data["trace_id"]
    }
    hitl_resp = requests.post(f"{BASE_URL}/api/v1/hitl/submit", json=hitl_payload, timeout=10)
    print(f"Blocked Draft HITL Submit Status: {hitl_resp.status_code}")
    assert hitl_resp.status_code == 400, f"Expected 400 for blocked draft approval, got {hitl_resp.status_code}"
    print("SUCCESS: Fictional entity was safely rejected and dispatch blocked!\n")

def test_tredence_real_entity():
    print("--- TEST 2: Real Entity 'Tredence Inc' ---")
    payload = {
        "lead_id": "test-tred-uuid-888",
        "lead_name": "Uditya Raj",
        "company_name": "Tredence Inc",
        "title": "Director of Enterprise AI Solutions",
        "email": "u.raj@tredence.com",
        "account_domain": "tredence.com",
        "focus_query": "Enterprise AI telemetry, multi-cloud migration, SOC 2 audit readiness",
        "force_live_search": True
    }
    
    resp = requests.post(f"{BASE_URL}/api/v1/pipeline/execute", json=payload, timeout=20)
    print(f"Status Code: {resp.status_code}")
    assert resp.status_code == 200
    data = resp.json()
    
    print(f"Workflow Status: {data.get('workflow_status')}")
    assert data.get("workflow_status") == "AWAITING_HITL_REVIEW"
    
    live_signals = data.get("live_signals", [])
    print(f"Discovered Live Signals Count: {len(live_signals)}")
    assert len(live_signals) > 0, "Expected live signals for Tredence Inc"
    for s in live_signals:
        print(f"  Signal: [{s.get('type')}] {s.get('title')} ({s.get('source_url')})")
        
    n2 = data["nodes"]["node2_rank"]
    print(f"Node 2 Output: {json.dumps(n2, indent=2)}")
    ranked = n2.get("ranked_data", {})
    icp_score = ranked.get("icp_fit_score", ranked.get("icp_score", 0.0))
    print(f"Node 2 ICP Score: {icp_score}")
    assert icp_score > 50.0
    
    n3 = data["nodes"]["node3_draft"]
    print(f"Node 3 Subject: {n3['draft_output']['subject']}")
    
    n4 = data["nodes"]["node4_critic"]
    print(f"Node 4 Verdict: {n4['critic_results']['verdict']}")
    
    print("SUCCESS: Real entity generated grounded outreach with live signals!\n")

def test_audit_event_logged():
    print("--- TEST 3: Cryptographic Audit Event Check ---")
    resp = requests.get(f"{BASE_URL}/api/v1/audit/events?limit=10", timeout=10)
    assert resp.status_code == 200
    events = resp.json().get("events", [])
    event_types = [e.get("event_type") for e in events]
    print(f"Recent Audit Event Types: {event_types[:6]}")
    assert "PIPELINE_SUPPRESSED_ZERO_SIGNALS" in event_types, "Expected PIPELINE_SUPPRESSED_ZERO_SIGNALS in audit events"
    print("SUCCESS: PIPELINE_SUPPRESSED_ZERO_SIGNALS correctly anchored in WORM audit log!\n")

if __name__ == "__main__":
    test_jamsesbond_zero_signal_guardrail()
    test_tredence_real_entity()
    test_audit_event_logged()
    print("ALL TESTS PASSED!")
