#!/usr/bin/env python3
from pathlib import Path
import ast

root = Path(__file__).resolve().parents[1]
run = (root / "run_aios.py").read_text()

checks = [
    ("shadow helper exists", "def shadow_possible_duplicate_review(" in run),
    ("shadow uses identity bridge", ".get_or_create_shadow_item(item)" in run),
    ("shadow creates possible_duplicate review", 'review_type="possible_duplicate"' in run),
    ("payload carries candidate title/score/confidence",
        '"candidate_task_title"' in run and '"match_score"' in run and '"confidence"' in run),
    ("shadow is idempotent on open reviews",
        "get_open_reviews_for_item(" in run and 'review.review_type == "possible_duplicate"' in run),
    ("Notion UI still renders", "inbox_review_ui.show_possible_duplicate(" in run),
    ("shadow runs after Notion UI", "shadow_possible_duplicate_review(match)" in run),
    ("shadow is Supabase-only", 'if AIOS_DATASTORE != "supabase":' in run),
    ("shadow is non-blocking", "[Possible Duplicate Shadow] Write failed:" in run),
    ("Supabase review authority marker exists", '"supabase_review_authority_v1"' in run),
]

ast.parse(run)

for label, ok in checks:
    print(f"{'PASS' if ok else 'FAIL'}: {label}")

if not all(ok for _, ok in checks):
    raise SystemExit("RESULT: POSSIBLE DUPLICATE SHADOW VALIDATION FAILED")

print("RESULT: POSSIBLE DUPLICATE SHADOW STRUCTURE VALID")
