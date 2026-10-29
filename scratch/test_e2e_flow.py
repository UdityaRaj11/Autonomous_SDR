import urllib.request
import json

base_url = "http://127.0.0.1:8000"

# 1. Fetch initial metrics
req = urllib.request.Request(f"{base_url}/api/v1/dashboard/metrics")
with urllib.request.urlopen(req) as r:
    init_m = json.loads(r.read().decode())
init_pipeline = init_m["pipeline_generated_usd"]
init_reviews = init_m["total_reviews_count"]

print(f"Initial: Pipeline=${init_pipeline:,.2f}, Reviews={init_reviews}")

# 2. Execute pipeline
exec_data = {
    "lead_name": "Uditya Raj",
    "company_name": "Tredence Inc",
    "title": "Director of Enterprise AI Solutions",
    "email": "u.raj@tredence.com",
    "account_domain": "tredence.com",
    "focus_query": "Live enterprise telemetry scaling",
    "force_live_search": True
}
req = urllib.request.Request(
    f"{base_url}/api/v1/pipeline/execute",
    data=json.dumps(exec_data).encode("utf-8"),
    headers={"Content-Type": "application/json"}
)
with urllib.request.urlopen(req) as r:
    pipe_res = json.loads(r.read().decode())

lead_id = pipe_res["lead_id"]
trace_id = pipe_res["trace_id"]
print(f"Executed pipeline: lead_id={lead_id}, trace_id={trace_id}")

# 3. Submit HITL review
hitl_data = {
    "lead_id": lead_id,
    "trace_id": trace_id,
    "reviewer_id": "sdr-user-5541",
    "action": "APPROVED_UNMODIFIED",
    "original_subject": pipe_res["nodes"]["node3_draft"]["draft_output"]["subject"],
    "original_body": pipe_res["nodes"]["node3_draft"]["draft_output"]["body"],
    "final_subject": pipe_res["nodes"]["node3_draft"]["draft_output"]["subject"],
    "final_body": pipe_res["nodes"]["node3_draft"]["draft_output"]["body"],
    "feedback_tags": ["tested_e2e_update"],
    "review_duration_seconds": 15
}
req = urllib.request.Request(
    f"{base_url}/api/v1/hitl/submit",
    data=json.dumps(hitl_data).encode("utf-8"),
    headers={"Content-Type": "application/json"}
)
with urllib.request.urlopen(req) as r:
    hitl_res = json.loads(r.read().decode())
print("HITL Recorded:", hitl_res)

# 4. Fetch updated metrics
req = urllib.request.Request(f"{base_url}/api/v1/dashboard/metrics")
with urllib.request.urlopen(req) as r:
    up_m = json.loads(r.read().decode())

print(f"Updated: Pipeline=${up_m['pipeline_generated_usd']:,.2f}, Reviews={up_m['total_reviews_count']}")
assert up_m["total_reviews_count"] == init_reviews + 1
assert up_m["pipeline_generated_usd"] == init_pipeline + 25000.0
print("SUCCESS: Dashboard metrics updated dynamically by exactly +$25,000!")

# 5. Check latest audit event
req = urllib.request.Request(f"{base_url}/api/v1/audit/events?limit=2")
with urllib.request.urlopen(req) as r:
    audit_data = json.loads(r.read().decode())
latest_ev = audit_data["events"][0]
print("Latest Audit Event:", latest_ev["event_type"])
print("Company Name:", latest_ev.get("company_name"))
print("Lead Name:", latest_ev.get("lead_name"))
assert latest_ev["company_name"] == "Tredence Inc"
print("SUCCESS: Audit trail contains verified company name and prospect!")
