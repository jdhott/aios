#!/usr/bin/env python3
from pathlib import Path
import ast

root = Path(__file__).resolve().parents[1]
text = (root / "run_aios.py").read_text()
ast.parse(text)

checks = [
    ("local SupabaseStore import",
     "from aios.storage.supabase_store import SupabaseStore as _ClarificationSupabaseStore" in text),
    ("local InboxRepository import",
     "from aios.storage.inbox_repository import InboxRepository as _ClarificationInboxRepository" in text),
    ("local InboxReviewRepository import",
     "from aios.review.repository import InboxReviewRepository as _ClarificationInboxReviewRepository" in text),
    ("localized aliases used",
     "_clarification_shadow_store = _ClarificationSupabaseStore()" in text
     and "clarification_shadow_inbox_repo = _ClarificationInboxRepository(" in text
     and "clarification_shadow_review_repo = _ClarificationInboxReviewRepository(" in text),
    ("bootstrap marker exists",
     "[Clarification Shadow] Bootstrap imports localized" in text),
    ("shadow integration remains present",
     "shadow_clarification_review(" in text),
    ("bootstrap remains non-blocking",
     "[Clarification Shadow] Bootstrap failed:" in text),
]

for label, ok in checks:
    print(f"{'PASS' if ok else 'FAIL'}: {label}")

if not all(ok for _, ok in checks):
    raise SystemExit("RESULT: CLARIFICATION SHADOW BOOTSTRAP FIX VALIDATION FAILED")

print("RESULT: CLARIFICATION SHADOW BOOTSTRAP FIX STRUCTURE VALID")
