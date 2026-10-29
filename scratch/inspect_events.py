import sys
sys.path.insert(0, ".")
from backend.compliance.audit_store import CryptographicAuditStore

audit = CryptographicAuditStore(auto_seed=True)
events = audit.list_events(limit=5)
for e in events:
    print("--- Event ---")
    print("Type:", e["event_type"])
    print("Lead ID:", e["lead_id"])
    print("Actor:", e["actor"])
    print("Payload keys:", list(e["payload"].keys()))
    print("Payload:", e["payload"])
