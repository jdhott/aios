#!/usr/bin/env python3

from pathlib import Path
import ast


root = Path(__file__).resolve().parents[1]
run = (root / "run_aios.py").read_text()


checks = [
    (
        "distinct staging list exists",
        "pending_reevaluated_distinct = []"
        in run,
    ),
    (
        "distinct inbox identity guard exists",
        "pending_reevaluated_distinct_inbox_ids"
        in run,
    ),
    (
        "normal classification skips staged distinct",
        "Skipping normal inbox classification"
        in run,
    ),
    (
        "distinct resumes normal task processing",
        "PROCESSING RE-EVALUATED DISTINCT:"
        in run,
    ),
    (
        "distinct requires created pages",
        "Distinct task creation produced no task"
        in run,
    ),
    (
        "distinct resolves only after creation",
        'action="reevaluated_distinct"'
        in run,
    ),
    (
        "created IDs are recorded",
        "created_task_ids=created_task_ids"
        in run,
    ),
    (
        "review inbox lifecycle helper exists",
        "def _mark_duplicate_review_inbox_processed("
        in run,
    ),
    (
        "failure leaves review pending",
        "Distinct task creation failed; review remains pending"
        in run,
    ),
]


ast.parse(run)

failed = []

for label, ok in checks:
    print(
        f"{'PASS' if ok else 'FAIL'}: {label}"
    )

    if not ok:
        failed.append(label)


if failed:
    raise SystemExit(
        "RESULT: DISTINCT RE-EVALUATION "
        "VALIDATION FAILED: "
        + ", ".join(failed)
    )


print(
    "RESULT: POSSIBLE DUPLICATE RE-EVALUATION "
    "DISTINCT V1 STRUCTURE VALID"
)
