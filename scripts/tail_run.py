import subprocess
import sys
import json
from datetime import datetime

cmd = [
    "C:\\WINDOWS\\System32\\wsl.exe", "-d", "Ubuntu-24.04", "-e",
    "gcloud", "logging", "read",
    "resource.type=cloud_run_revision AND resource.labels.service_name=nasdaq-multi-agent AND resource.labels.revision_name=nasdaq-multi-agent-00022-rhf",
    "--limit=1000", "--format=json"
]

res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
if res.returncode != 0:
    print(res.stderr)
    sys.exit(1)

logs = json.loads(res.stdout)
valid_logs = []
for entry in logs:
    t_str = entry.get("timestamp")
    if t_str:
        t_str = t_str.replace("Z", "+00:00")
        t = datetime.fromisoformat(t_str).replace(tzinfo=None)
        valid_logs.append((t, entry.get("textPayload", "")))

valid_logs.sort(key=lambda x: x[0])
print(f"DEBUG: Retrieved {len(logs)} log entries for revision nasdaq-multi-agent-00021-qws")
for t, payload in valid_logs:
    if payload.strip():
        print(f"[{t.strftime('%H:%M:%S')}] {payload.strip()}")
