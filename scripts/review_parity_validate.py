#!/usr/bin/env python3

from pathlib import Path
import ast

root = Path(__file__).resolve().parents[1]

files = {
    "run": root / "run_aios.py",
    "service": root / "aios/services/review_service.py",
    "api": root / "aios/api/app.py",
    "web": root / "aios/web_capture/app.py",
    "duplicate_transitions": root / "aios/review/possible_duplicate_transitions.py",
    "clarification_transitions": root / "aios/review/clarification_transitions.py",
}

texts = {}

for name, path in files.items():
    if not path.exists():
        raise SystemExit(f"FAIL: required file missing: {path}")
    texts[name] = path.read_text()
    ast.parse(texts[name])

run = texts["run"]
service = texts["service"]
api = texts["api"]
web = texts["web"]
dup = texts["duplicate_transitions"]
clar = texts["clarification_transitions"]

checks = [

    # ---------------------------------------------------------
    # Possible duplicate authority
    # ---------------------------------------------------------

    (
        "duplicate: shared transition helper exists",
        "def resolve_possible_duplicate_review(" in dup,
    ),
    (
        "duplicate: all three decisions supported",
        all(
            action in dup
            for action in (
                '"link_existing"',
                '"create_anyway"',
                '"ignore"',
            )
        ),
    ),
    (
        "duplicate: Supabase review authority active",
        '"authority": "supabase_review_authority_v1"' in run,
    ),
    (
        "duplicate: processor reads open Supabase review",
        "def _open_possible_duplicate_review(item):" in run,
    ),
    (
        "duplicate: link-existing processor path exists",
        '_resolve_possible_duplicate_now(match, "link_existing")' in run,
    ),
    (
        "duplicate: keep-separate processor path exists",
        '_resolve_possible_duplicate_now(match, "ignore")' in run,
    ),
    (
        "duplicate: create-anyway staging exists",
        "_stage_possible_duplicate_create_anyway(match)" in run,
    ),
    (
        "duplicate: staged create-anyway resolves after creation",
        "_resolve_staged_possible_duplicate_create_anyway(item, created_pages)"
        in run,
    ),
    (
        "duplicate: web supports reevaluation",
        "def possible_duplicate_reevaluate_web(" in web,
    ),
    (
        "duplicate: web supports use-existing",
        "def possible_duplicate_use_existing_web(" in web,
    ),
    (
        "duplicate: web supports create-new",
        "def possible_duplicate_create_new_web(" in web,
    ),
    (
        "duplicate: service supports reevaluation",
        "def request_possible_duplicate_reevaluation(" in service,
    ),
    (
        "duplicate: service supports create-anyway",
        "def request_possible_duplicate_create_anyway(" in service,
    ),
    (
        "duplicate: service resolves review",
        "def resolve_possible_duplicate(" in service,
    ),

    # ---------------------------------------------------------
    # Clarification authority
    # ---------------------------------------------------------

    (
        "clarification: shared transition helpers exist",
        all(
            marker in clar
            for marker in (
                "def mark_clarification_awaiting_answer(",
                "def mark_clarification_pending_confirmation(",
                "def resolve_clarification_review(",
            )
        ),
    ),
    (
        "clarification: awaiting-answer state exists",
        '"awaiting_answer"' in clar,
    ),
    (
        "clarification: pending-confirmation state exists",
        '"pending_confirmation"' in clar,
    ),
    (
        "clarification: service requests targeted question",
        "def request_clarification_question(" in service,
    ),
    (
        "clarification: service accepts answer",
        "def submit_clarification_answer(" in service,
    ),
    (
        "clarification: service resolves accepted clarification",
        "def resolve_clarification(" in service,
    ),
    (
        "clarification: web supports delete task",
        "def clarification_delete_task_web(" in web,
    ),
    (
        "clarification: web supports targeted question",
        "def clarification_request_question_web(" in web,
    ),
    (
        "clarification: web supports answer",
        "def clarification_answer_web(" in web,
    ),
    (
        "clarification: web supports accepted clarification",
        "def clarification_use_web(" in web,
    ),
    (
        "clarification: API uses shared awaiting-answer transition",
        "mark_clarification_awaiting_answer(" in api,
    ),
    (
        "clarification: API uses shared pending-confirmation transition",
        "mark_clarification_pending_confirmation(" in api,
    ),
    (
        "clarification: processor configures Supabase transitions",
        "[Clarification Review] State transition helpers configured" in run,
    ),
    (
        "clarification: legacy Notion runtime removed",
        "legacy Notion clarification runtime removed" in run,
    ),

    # ---------------------------------------------------------
    # Legacy runtime removal
    # ---------------------------------------------------------

    (
        "legacy: old clarification module removed",
        not (root / "aios/clarification.py").exists(),
    ),
    (
        "legacy: old Notion duplicate review module removed",
        not (root / "aios/notion/duplicate_review.py").exists(),
    ),
]

failed = False

for label, ok in checks:
    print(("PASS" if ok else "FAIL") + ": " + label)
    failed |= not ok

if failed:
    raise SystemExit("RESULT: REVIEW PARITY VALIDATION FAILED")

print()
print("RESULT: REVIEW PARITY STRUCTURE VALID")
print("Possible Duplicates: SUPABASE/WEB PARITY")
print("Clarification: SUPABASE/WEB PARITY")
print("Legacy review runtime: REMOVED")
