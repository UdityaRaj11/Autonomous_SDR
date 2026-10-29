import sys, os
sys.path.insert(0, os.path.abspath("."))
import urllib.request, json

req = urllib.request.urlopen("http://127.0.0.1:8000/api/v1/audit/events?limit=20")
res = json.loads(req.read().decode())
print("Total events:", res["total_records"])
print("Integrity:", res["chain_integrity"])
for i, ev in enumerate(res["events"][:10]):
    print(f"[{i}] {ev['event_timestamp']} | {ev['event_type']} | {ev['lead_id']} | actor: {ev['actor']['actor_type']}")
