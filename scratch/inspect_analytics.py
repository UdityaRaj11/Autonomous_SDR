import sys
sys.path.insert(0, ".")
from backend.db.database import DatabaseManager

db = DatabaseManager()
analytics = db.get_dashboard_analytics()

print("Pipeline USD:", analytics["pipeline_generated_usd"])
print("Approval rate:", analytics["draft_approval_rate_percent"])
print("Total reviews:", analytics["total_reviews_count"])
print("Throughput labels:", analytics["charts"]["throughput"]["labels"])
print("Throughput clean:", analytics["charts"]["throughput"]["approved_clean"])
print("Throughput edited:", analytics["charts"]["throughput"]["approved_with_edits"])
print("Throughput rejected:", analytics["charts"]["throughput"]["rejected"])
