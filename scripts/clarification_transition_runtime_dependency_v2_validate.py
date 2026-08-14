#!/usr/bin/env python3
from pathlib import Path
import ast

root = Path(__file__).resolve().parents[1]
run_text = (root / "run_aios.py").read_text()
clar_text = (root / "aios/clarification.py").read_text()

checks = [
    (
        "runtime refresh marker exists",
        "[Clarification Shadow] Runtime dependencies refreshed" in run_text,
    ),
    (
        "runtime refresh occurs after transition helper config",
        run_text.find("[Clarification Shadow] State transition helpers configured")
        < run_text.find(
            "clarification_helpers.configure_clarification_module(globals())",
            run_text.find("[Clarification Shadow] State transition helpers configured"),
        ),
    ),
    (
        "lookup guards datastore access",
        'globals().get("AIOS_DATASTORE")' in clar_text,
    ),
    (
        "lookup guards review repository access",
        "clarification_shadow_review_repo" in clar_text,
    ),
    (
        "lookup uses guarded local repository",
        "review_repo.store.client" in clar_text
        and "review_repo.row_to_review(row)" in clar_text,
    ),
    (
        "unsafe direct repository guard removed",
        "if clarification_shadow_review_repo is None:" not in clar_text,
    ),
    (
        "transition writes remain non-blocking",
        "[Clarification Shadow] Transition write failed:" in clar_text,
    ),
]

ast.parse(run_text)
ast.parse(clar_text)

for label, ok in checks:
    print(f"{'PASS' if ok else 'FAIL'}: {label}")

if not all(ok for _, ok in checks):
    raise SystemExit(
        "RESULT: CLARIFICATION TRANSITION RUNTIME DEPENDENCY FIX V2 VALIDATION FAILED"
    )

print(
    "RESULT: CLARIFICATION TRANSITION RUNTIME DEPENDENCY FIX V2 STRUCTURE VALID"
)
