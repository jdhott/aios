#!/usr/bin/env python3
from __future__ import annotations
import ast
from pathlib import Path

root = Path(__file__).resolve().parents[1]
text = (root / 'run_aios.py').read_text()
ast.parse(text)

checks = [
    ('Supabase/web authority marker', 'possible-duplicate-supabase-web-v1' in text),
    ('Notion UI is legacy-mode only', 'if AIOS_DATASTORE == "notion":\n    from aios.notion import duplicate_review' in text),
    ('Supabase review upsert exists', 'def upsert_possible_duplicate_review(match):' in text),
    ('Supabase classification uses review upsert', 'if AIOS_DATASTORE == "supabase":\n                upsert_possible_duplicate_review(match)' in text),
    ('Notion rendering is explicit fallback', 'elif inbox_review_ui is not None:\n                inbox_review_ui.show_possible_duplicate(' in text),
    ('Notion action reads are gated to legacy mode', 'and AIOS_DATASTORE == "notion"' in text and '.get_possible_duplicate_action(item)' in text),
    ('Supabase action is checked first', '_requested_possible_duplicate_action(' in text),
    ('No unconditional Notion duplicate UI construction', '\ninbox_review_ui = duplicate_review_ui.NotionInboxReviewUI()\n' not in text),
]
for label, ok in checks:
    print(f"{'PASS' if ok else 'FAIL'}: {label}")
if not all(ok for _, ok in checks):
    raise SystemExit('RESULT: POSSIBLE DUPLICATE SUPABASE CUTOVER V1 VALIDATION FAILED')
print('RESULT: POSSIBLE DUPLICATE SUPABASE CUTOVER V1 STRUCTURE VALID')
