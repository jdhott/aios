#!/usr/bin/env python3
from pathlib import Path
import ast

root = Path(__file__).resolve().parents[1]
service = (root / "aios/services/review_service.py").read_text()
ast.parse(service)

checks = [
    ("phase marker", 'APP_REVIEW_RESOLUTION_SERVICE_VERSION = "app-service-boundary-v1-phase2.2"' in service),
    ("clarification awaiting method", "def mark_clarification_awaiting_answer(" in service),
    ("clarification confirmation method", "def mark_clarification_pending_confirmation(" in service),
    ("clarification resolve method", "def resolve_clarification(" in service),
    ("duplicate resolve method", "def resolve_possible_duplicate(" in service),
    ("create-anyway guard", 'action == "create_anyway" and not created_task_ids' in service),
    ("review guard", "def _require_review(" in service and 'review.state == "resolved"' in service),
    ("Notion-independent", "notion" not in service.lower()),
]
for label, ok in checks:
    print(f"{'PASS' if ok else 'FAIL'}: {label}")
if not all(ok for _, ok in checks):
    raise SystemExit("RESULT: APP REVIEW RESOLUTION SERVICE PHASE 2.2 VALIDATION FAILED")
print("RESULT: APP REVIEW RESOLUTION SERVICE PHASE 2.2 STRUCTURE VALID")
