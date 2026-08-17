#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
projects = (ROOT / "aios/projects.py").read_text()
config = (ROOT / "aios/job/config.py").read_text()
deploy = (ROOT / "scripts/deploy_cloud_run_job.sh").read_text()

checks = [
    ("telemetry writer is compatibility no-op", "Legacy compatibility no-op" in projects),
    ("Notion telemetry pages API removed", "NOTION_TOPOLOGY_TELEMETRY_DATABASE_ID" not in projects),
    ("runtime test telemetry removed", "telemetry_runtime_test" not in projects),
    ("job config no longer requires telemetry DB", "NOTION_TOPOLOGY_TELEMETRY_DATABASE_ID" not in config),
    ("deployment no longer requires telemetry DB", "NOTION_TOPOLOGY_TELEMETRY_DATABASE_ID" not in deploy),
    ("project cognition call boundary preserved", "log_topology_telemetry_event(" in projects),
]
failed=[]
for label, ok in checks:
    print(("PASS" if ok else "FAIL") + ": " + label)
    if not ok: failed.append(label)
if failed:
    print("RESULT: TOPOLOGY TELEMETRY RETIREMENT V1 VALIDATION FAILED")
    raise SystemExit(1)
print("RESULT: TOPOLOGY TELEMETRY RETIREMENT V1 STRUCTURE VALID")
