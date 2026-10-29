import sys, os
sys.path.insert(0, os.path.abspath("."))
from backend.db.database import DatabaseManager
import json

db = DatabaseManager()
a = db.get_dashboard_analytics()
print("Total reviews:", a["total_reviews_count"])
print("Total runs:", a["total_runs_count"])
print("Pipeline USD:", a["pipeline_generated_usd"])
print("Approval rate:", a["draft_approval_rate_percent"])
print("Throughput labels:", a["charts"]["throughput"]["labels"])
print("Throughput clean:", a["charts"]["throughput"]["approved_clean"])
print("Throughput edited:", a["charts"]["throughput"]["approved_with_edits"])
print("Throughput rejected:", a["charts"]["throughput"]["rejected"])
print("Reps labels:", a["charts"]["reps"]["labels"])
print("Reps durations:", a["charts"]["reps"]["avg_duration_sec"])
print("Signals labels:", a["charts"]["signals"]["labels"])
print("Signals dispatched:", a["charts"]["signals"]["dispatched_count"])
print("Hallucination counts:", a["charts"]["hallucination"]["draft_counts"])
