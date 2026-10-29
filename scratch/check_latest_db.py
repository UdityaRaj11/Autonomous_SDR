import sys, os
sys.path.insert(0, os.path.abspath("."))
from backend.db.database import DatabaseManager

db = DatabaseManager()
with db.get_connection() as conn:
    c = conn.cursor()
    print("=== LATEST 5 AGENT RUNS ===")
    for r in c.execute("SELECT r.created_at, l.company_name, l.lead_name, r.critic_verdict, r.total_tokens, r.total_cost_usd, r.draft_subject FROM agent_runs r JOIN leads l ON r.lead_id = l.id ORDER BY r.created_at DESC LIMIT 5").fetchall():
        print(dict(r))
    
    print("\n=== LATEST 5 HITL REVIEWS ===")
    for r in c.execute("SELECT hr.created_at, l.company_name, l.lead_name, hr.action, hr.reviewer_id, hr.review_duration_ms, hr.character_edit_distance_ratio FROM hitl_reviews hr JOIN leads l ON hr.lead_id = l.id ORDER BY hr.created_at DESC LIMIT 5").fetchall():
        print(dict(r))
