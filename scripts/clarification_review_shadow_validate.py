#!/usr/bin/env python3
from pathlib import Path
import ast

root = Path(__file__).resolve().parents[1]
run_text = (root / "run_aios.py").read_text()
shadow_text = (root / "aios/review/clarification_shadow.py").read_text()

checks = [
    ("shadow helper module exists", "def shadow_clarification_review(" in shadow_text),
    ("uses inbox identity bridge", ".get_or_create_shadow_item(item)" in shadow_text),
    ("reuses open clarification review",
        "get_open_reviews_for_item(" in shadow_text and 'review.review_type == "clarification"' in shadow_text),
    ("creates pending clarification review",
        'review_type="clarification"' in shadow_text and 'state="pending"' in shadow_text),
    ("payload includes proposal semantics",
        all(x in shadow_text for x in [
            '"original_text"', '"proposed_text"', '"clarification_mode"',
            '"clarification_reason"', '"notion_task_page_id"',
            '"task_title"', '"notion_shadow_only"'
        ])),
    ("maybe_add receives InboxItem",
        "def maybe_add_clarification_blocks(first_page, task_title, original_title, item):" in run_text),
    ("Notion render precedes shadow write",
        run_text.find("render_result = append_clarification_blocks(") <
        run_text.find("review, created = shadow_clarification_review(")),
    ("shadow non-blocking", "[Clarification Shadow] Write failed:" in run_text),
    ("process_task_item passes original item", "item=item," in run_text),
]

ast.parse(run_text)
ast.parse(shadow_text)

for label, ok in checks:
    print(f"{'PASS' if ok else 'FAIL'}: {label}")

if not all(ok for _, ok in checks):
    raise SystemExit("RESULT: CLARIFICATION REVIEW SHADOW V1 VALIDATION FAILED")

print("RESULT: CLARIFICATION REVIEW SHADOW V1 STRUCTURE VALID")
