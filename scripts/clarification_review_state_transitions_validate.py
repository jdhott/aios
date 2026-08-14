#!/usr/bin/env python3
from pathlib import Path
import ast

root = Path(__file__).resolve().parents[1]
run_text = (root / "run_aios.py").read_text()
clar_text = (root / "aios/clarification.py").read_text()
trans_text = (root / "aios/review/clarification_transitions.py").read_text()

checks = [
    ("transition helper module exists",
     "def mark_clarification_awaiting_answer(" in trans_text
     and "def mark_clarification_pending_confirmation(" in trans_text
     and "def resolve_clarification_review(" in trans_text),
    ("awaiting_answer transition exists",
     '"awaiting_answer"' in trans_text
     and "_shadow_mark_awaiting_answer(" in clar_text),
    ("pending_confirmation transition exists",
     '"pending_confirmation"' in trans_text
     and "_shadow_mark_pending_confirmation(" in clar_text),
    ("resolved transition exists",
     "review_repo.resolve_review(" in trans_text
     and "_shadow_resolve_clarification(" in clar_text),
    ("Notion question render precedes shadow transition",
     clar_text.find('print("Added one targeted clarification question (verified)")')
     < clar_text.find("_shadow_mark_awaiting_answer(",
                      clar_text.find('print("Added one targeted clarification question (verified)")'))),
    ("answer rebuild precedes shadow transition",
     clar_text.find("rebuild_result = rebuild_clarification_blocks(")
     < clar_text.find("_shadow_mark_pending_confirmation(",
                      clar_text.find("rebuild_result = rebuild_clarification_blocks("))),
    ("accepted task update precedes resolved transition",
     clar_text.find("if not updated_page:")
     < clar_text.find("_shadow_resolve_clarification(",
                      clar_text.find("if not updated_page:"))),
    ("transition failures non-blocking",
     "[Clarification Shadow] Transition write failed:" in clar_text),
    ("runtime transition marker exists",
     "[Clarification Shadow] State transition helpers configured" in run_text),
]

for text in (run_text, clar_text, trans_text):
    ast.parse(text)

for label, ok in checks:
    print(f"{'PASS' if ok else 'FAIL'}: {label}")

if not all(ok for _, ok in checks):
    raise SystemExit("RESULT: CLARIFICATION REVIEW STATE TRANSITIONS VALIDATION FAILED")

print("RESULT: CLARIFICATION REVIEW STATE TRANSITIONS STRUCTURE VALID")
