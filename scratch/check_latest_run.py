import sqlite3
import sys

sys.stdout.reconfigure(encoding='utf-8')

conn = sqlite3.connect('sdr_engine.db')
c = conn.cursor()
c.execute('SELECT lead_id, draft_subject, draft_body, critic_verdict, created_at FROM agent_runs ORDER BY created_at DESC LIMIT 3;')
rows = c.fetchall()
for i, row in enumerate(rows):
    print(f"\n=== Run {i+1} (at {row[4]}) ===")
    print("Lead ID:", row[0])
    print("Subject:", row[1])
    print("Body:\n", row[2])
    print("Critic Verdict:", row[3])

    c.execute('SELECT signal_type, title, source_name, source_uri FROM signals WHERE lead_id = ?;', (row[0],))
    sigs = c.fetchall()
    print("Signals count:", len(sigs))
    for s in sigs:
        print(" -", s)
