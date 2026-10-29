import urllib.request
import json

base_url = "http://127.0.0.1:8000"

# 1. Health
with urllib.request.urlopen(f"{base_url}/api/v1/health") as response:
    health = json.loads(response.read().decode())
    print("Health Status:", health.get("status"))
    print("Headers:", dict(response.headers))

# 2. Metrics
with urllib.request.urlopen(f"{base_url}/api/v1/dashboard/metrics") as response:
    metrics = json.loads(response.read().decode())
    print("Pipeline Generated USD:", metrics.get("pipeline_generated_usd"))
    print("Total Reviews Count:", metrics.get("total_reviews_count"))
    print("Draft Approval Rate %:", metrics.get("draft_approval_rate_percent"))
    print("Today Clean:", metrics["charts"]["throughput"]["approved_clean"][-1])

# 3. Events
with urllib.request.urlopen(f"{base_url}/api/v1/audit/events?limit=3") as response:
    events = json.loads(response.read().decode())
    print("Audit Events Count:", len(events.get("events", [])))
    for ev in events.get("events", [])[:2]:
        print(" - Event:", ev["event_type"], "| Company:", ev.get("company_name"), "| Lead:", ev.get("lead_name"))
