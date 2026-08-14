#!/usr/bin/env python3
from pathlib import Path
import ast
root=Path(__file__).resolve().parents[1]
notion=(root/"aios/notion/duplicate_review.py").read_text()
run=(root/"run_aios.py").read_text()
cleanup=(root/"scripts/app_service_boundary_phase1_test_recovery.py").read_text()
for t in (notion,run,cleanup): ast.parse(t)
checks=[
("source-aware marker",'SOURCE_AWARE_DUPLICATE_REVIEW_VERSION = "app-service-boundary-v1-phase1.2"' in notion),
("skip non-Notion presentation",'if item.source != "notion":' in notion and "Skipping Notion duplicate presentation" in notion),
("skip non-Notion action read",notion.count('if item.source != "notion":')>=2),
("runtime marker",'SOURCE_AWARE_REVIEW_PRESENTATION_VERSION = "app-service-boundary-v1-phase1.2"' in run),
("five recovery task ids",cleanup.count('("')>=5 and cleanup.count("Clarify next action:")>=5),
("flashlight preserved",'FLASHLIGHT_INBOX_ID = "cc097591-3968-4e32-913f-a85274502480"' in cleanup),
("explicit confirmation","CLEAN-PHASE1-TEST-ARTIFACTS" in cleanup),
]
for label,ok in checks: print(f"{'PASS' if ok else 'FAIL'}: {label}")
if not all(ok for _,ok in checks): raise SystemExit("RESULT: APP SERVICE BOUNDARY PHASE 1.2 VALIDATION FAILED")
print("RESULT: APP SERVICE BOUNDARY PHASE 1.2 STRUCTURE VALID")
