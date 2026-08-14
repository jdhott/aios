#!/usr/bin/env python3
from pathlib import Path
import ast

root = Path(__file__).resolve().parents[1]
app = (root / "aios/api/app.py").read_text()
scheduler = (
    root / "scripts/configure_scheduled_compatibility_trigger.sh"
).read_text()
pause = (
    root / "scripts/pause_scheduled_compatibility_trigger.sh"
).read_text()

ast.parse(app)

checks = [
    ("scheduled compatibility marker",
     'AIOS_SCHEDULED_COMPAT_TRIGGER_VERSION = "scheduled-compat-trigger-v1"' in app),
    ("processing request endpoint exists", '"/processing/request"' in app),
    ("endpoint uses canonical trigger helper", "result = _request_processor_run()" in app),
    ("trigger helper reports coalesced requests", '"status": "coalesced"' in app),
    ("trigger failures return recoverable status",
     '"status": "failed"' in app and "processing remains requested" in app),
    ("scheduler uses OIDC",
     "--oidc-service-account-email" in scheduler and "--oidc-token-audience" in scheduler),
    ("scheduler targets private API endpoint", '${SERVICE_URL}/processing/request' in scheduler),
    ("quarter-hour daytime schedule", '*/15 5-20 * * *' in scheduler),
    ("exact 21:00 final schedule", '0 21 * * *' in scheduler),
    ("Toronto timezone", 'America/Toronto' in scheduler),
    ("scheduler service account gets API invoker", "roles/run.invoker" in scheduler),
    ("scheduler API enabled", "cloudscheduler.googleapis.com" in scheduler),
    ("pause script covers both jobs",
     "aios-compat-quarter-hour" in pause and "aios-compat-2100" in pause),
]

for label, ok in checks:
    print(f"{'PASS' if ok else 'FAIL'}: {label}")

if not all(ok for _, ok in checks):
    raise SystemExit("RESULT: SCHEDULED COMPATIBILITY TRIGGER V1 VALIDATION FAILED")

print("RESULT: SCHEDULED COMPATIBILITY TRIGGER V1 STRUCTURE VALID")
