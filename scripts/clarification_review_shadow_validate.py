#!/usr/bin/env python3
from pathlib import Path
import ast

root = Path(__file__).resolve().parents[1]
run_text = (root / "run_aios.py").read_text()
review_text = (root / "aios/review/clarification_shadow.py").read_text()

checks = [
    ("authoritative clarification helper exists",
     "def create_clarification_review(" in review_text),
    ("uses source-neutral inbox review identity",
     ".get_review_row_for_item(" in review_text),
    ("reuses open clarification review",
     "get_open_reviews_for_item(" in review_text
     and 'review.review_type == "clarification"' in review_text),
    ("creates pending clarification review",
     'review_type="clarification"' in review_text
     and 'state="pending"' in review_text),
    ("payload carries authoritative task identity",
     all(x in review_text for x in [
         '"original_text"', '"proposed_text"', '"task_id"',
         '"task_title"', '"clarification_mode"',
         '"clarification_reason"', '"authority"'
     ])),
    ("Supabase authority version exists",
     "supabase-clarification-review-v1" in review_text),
    ("runtime creates authoritative clarification review",
     "review, created = create_clarification_review(" in run_text),
    ("runtime passes Supabase task id",
     "task_id=task_id" in run_text),
    ("legacy Notion clarification UI is isolated",
     'if AIOS_DATASTORE == "notion":' in run_text
     and "Legacy Notion clarification UI configured" in run_text),
]

ast.parse(run_text)
ast.parse(review_text)

for label, ok in checks:
    print(f"{'PASS' if ok else 'FAIL'}: {label}")

if not all(ok for _, ok in checks):
    raise SystemExit("RESULT: CLARIFICATION REVIEW AUTHORITY VALIDATION FAILED")

print("RESULT: CLARIFICATION REVIEW AUTHORITY STRUCTURE VALID")
