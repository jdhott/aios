#!/usr/bin/env python3
from pathlib import Path
import ast

root = Path(__file__).resolve().parents[1]
app = (root / "aios/api/app.py").read_text()

ast.parse(app)

checks = [
    ("v1.1 marker", 'AIOS_REVIEW_LIFECYCLE_FIX_VERSION = "cloud-workflow-lifecycle-v1.1"' in app),
    ("shadow row load", "review_row = repo.get_row(review.inbox_item_id)" in app),
    ("shadow row processed", "repo.mark_processed(review.inbox_item_id)" in app),
    ("shadow marker checked", 'source_metadata.get("shadow")' in app),
    ("origin source_item_id followed", 'review_row.get("source_item_id")' in app),
    ("origin row loaded", "original_row = repo.get_row(original_inbox_id)" in app),
    ("origin row processed", "repo.mark_processed(original_inbox_id)" in app),
    ("self-reference guard", "original_inbox_id == review.inbox_item_id" in app),
]

for label, ok in checks:
    print(f"{'PASS' if ok else 'FAIL'}: {label}")

if not all(ok for _, ok in checks):
    raise SystemExit("RESULT: CLOUD WORKFLOW LIFECYCLE FIX V1.1 VALIDATION FAILED")

print("RESULT: CLOUD WORKFLOW LIFECYCLE FIX V1.1 STRUCTURE VALID")
