import urllib.request

html = urllib.request.urlopen("http://127.0.0.1:8000/").read().decode()
# Check if kpi-pipeline-val is in html
print("Has kpi-pipeline-val:", "kpi-pipeline-val" in html)
print("Has chartThroughput:", "chartThroughput" in html)
print("Has syncDashboardFromBackend:", "syncDashboardFromBackend" in html)

# Find KPI values in HTML
import re
kpis = re.findall(r'<div[^>]*id="kpi-[^"]*"[^>]*>([^<]*)</div>', html)
print("KPI element texts in HTML:", kpis)
