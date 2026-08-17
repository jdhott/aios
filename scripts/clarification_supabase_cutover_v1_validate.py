#!/usr/bin/env python3
from __future__ import annotations

import ast
from pathlib import Path

root = Path(__file__).resolve().parents[1]
run_text = (root / "run_aios.py").read_text()
service_text = (root / "aios/services/review_service.py").read_text()

ast.parse(run_text)
ast.parse(service_text)

legacy_start = run_text.find('if AIOS_DATASTORE == "notion":', run_text.find("# Clarification review authority"))
legacy_end = run_text.find("clarification_shadow_inbox_repo = None", legacy_start)
legacy_block = run_text[legacy_start:legacy_end] if legacy_start >= 0 and legacy_end >= 0 else ""

supabase_start = run_text.find('if AIOS_DATASTORE == "supabase":', legacy_end)
supabase_end = run_text.find("# Possible Duplicate", supabase_start)
if supabase_end < 0:
    supabase_end = run_text.find("# Legacy Notion mode", supabase_start)
supabase_block = run_text[supabase_start:supabase_end] if supabase_start >= 0 and supabase_end >= 0 else ""

checks = [
    (
        "Supabase/web clarification authority marker",
        "Supabase/web authority configured" in run_text,
    ),
    (
        "legacy clarification module is Notion-only",
        'if AIOS_DATASTORE == "notion":' in run_text
        and "from aios import clarification as clarification_helpers" in legacy_block
        and "configure_clarification_module(globals())" in legacy_block,
    ),
    (
        "Supabase runtime does not initialize legacy clarification module",
        "clarification_helpers.configure_clarification_module(globals())" not in supabase_block,
    ),
    (
        "normal runtime no longer initializes Notion mirror title writer",
        "NotionTaskMirrorTitleWriter" not in run_text
        and "notion_task_mirror_title_writer" not in run_text,
    ),
    (
        "Notion clarification polling remains disabled in Supabase mode",
        "Notion clarification polling disabled" in run_text,
    ),
    (
        "Supabase clarification review repositories remain configured",
        "clarification_shadow_inbox_repo = _ClarificationInboxRepository(" in run_text
        and "clarification_shadow_review_repo = _ClarificationInboxReviewRepository(" in run_text,
    ),
    (
        "web requested clarification actions remain processor-owned",
        'requested_action == "ask_question"' in run_text
        and 'requested_action == "process_answer"' in run_text,
    ),
    (
        "new clarification reviews are written to Supabase",
        "def maybe_create_clarification_review(" in run_text
        and "create_clarification_review(" in run_text,
    ),
    (
        "accepted clarification remains human-authoritative",
        "def resolve_clarification(" in service_text
        and "Human acceptance is authoritative" in service_text
        and "self.task_repository.update_task(" in service_text
        and "prepare_task_title(" not in service_text,
    ),
]

for label, ok in checks:
    print(f"{'PASS' if ok else 'FAIL'}: {label}")

if not all(ok for _, ok in checks):
    raise SystemExit("RESULT: CLARIFICATION SUPABASE CUTOVER V1 VALIDATION FAILED")

print("RESULT: CLARIFICATION SUPABASE CUTOVER V1 STRUCTURE VALID")
