#!/usr/bin/env python3
from pathlib import Path
import ast

root = Path(__file__).resolve().parents[1]
run_text = (root / "run_aios.py").read_text()
trans_text = (root / "aios/review/clarification_transitions.py").read_text()
service_text = (root / "aios/services/review_service.py").read_text()
api_text = (root / "aios/api/app.py").read_text()

checks = [
    ("transition helper module exists",
     "def mark_clarification_awaiting_answer(" in trans_text
     and "def mark_clarification_pending_confirmation(" in trans_text
     and "def resolve_clarification_review(" in trans_text),
    ("awaiting_answer transition exists", '"awaiting_answer"' in trans_text),
    ("pending_confirmation transition exists", '"pending_confirmation"' in trans_text),
    ("resolved transition exists", "review_repo.resolve_review(" in trans_text),
    ("web review service uses shared transitions",
     "mark_clarification_awaiting_answer(" in service_text
     and "mark_clarification_pending_confirmation(" in service_text
     and "resolve_clarification_review(" in service_text),
    ("API exposes clarification state actions",
     "mark_clarification_awaiting_answer(" in api_text
     and "mark_clarification_pending_confirmation(" in api_text),
    ("processor keeps shared transition helpers available",
     "mark_clarification_awaiting_answer," in run_text
     and "mark_clarification_pending_confirmation," in run_text
     and "resolve_clarification_review," in run_text),
    ("Supabase runtime transition marker exists",
     "[Clarification Review] State transition helpers configured" in run_text),
    ("legacy Notion transition path is not initialized in Supabase mode",
     "legacy Notion clarification UI not initialized" in run_text),
]

for text in (run_text, trans_text, service_text, api_text):
    ast.parse(text)

for label, ok in checks:
    print(f"{'PASS' if ok else 'FAIL'}: {label}")

if not all(ok for _, ok in checks):
    raise SystemExit("RESULT: CLARIFICATION REVIEW STATE TRANSITIONS VALIDATION FAILED")

print("RESULT: CLARIFICATION REVIEW STATE TRANSITIONS STRUCTURE VALID")
