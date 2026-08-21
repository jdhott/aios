#!/usr/bin/env python3
from pathlib import Path

root = Path(__file__).resolve().parents[1]
policy = (root / "aios/processing/maintenance_policy.py").read_text()
run_aios = (root / "run_aios.py").read_text()
scheduler = (root / "scripts/configure_scheduled_compatibility_trigger.sh").read_text()

checks = [
    ("light maintenance version marker", "PROCESSOR_LIGHT_MAINTENANCE_VERSION" in policy),
    ("pending inbox helper", "def has_pending_inbox_work(" in policy),
    ("pending ai work helper", "def has_pending_ai_work(" in policy),
    ("pipeline activity helper", "def has_pipeline_activity(" in policy),
    ("heavy maintenance gate", "def should_run_heavy_ai_maintenance(" in policy),
    ("run_aios imports maintenance policy", "from aios.processing.maintenance_policy import" in run_aios),
    ("run_aios gates project detector", "Skipping project candidate detector on light run." in run_aios),
    ("run_aios gates project work", "Skipping project work refresh on light run." in run_aios),
    ("scheduler throttled to 30 minutes", "*/30 5-20 * * *" in scheduler),
]

for label, ok in checks:
    print(f"{'PASS' if ok else 'FAIL'}: {label}")

if not all(ok for _, ok in checks):
    raise SystemExit("RESULT: PROCESSOR LIGHT MAINTENANCE V1 VALIDATION FAILED")

print("RESULT: PROCESSOR LIGHT MAINTENANCE V1 STRUCTURE VALID")
