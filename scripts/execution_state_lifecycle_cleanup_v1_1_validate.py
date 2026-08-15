#!/usr/bin/env python3
from pathlib import Path
import ast

root = Path(__file__).resolve().parents[1]
source = (root / "aios/storage/execution_task_source.py").read_text()
ast.parse(source)

checks = [
    (
        "v1.1 marker",
        'EXECUTION_STATE_LIFECYCLE_CLEANUP_VERSION = "v1.1"' in source,
    ),
    (
        "active execution population requires open",
        "if task.is_open" in source,
    ),
    (
        "active execution population excludes done",
        "and not task.is_done" in source,
    ),
    (
        "active execution population excludes archived",
        "and not task.is_archived" in source,
    ),
    (
        "stale state cleanup retained",
        "execution_repository.clear_execution_state(" in source,
    ),
    (
        "closed lifecycle conditions retained",
        "task.is_done" in source
        and "task.is_archived" in source
        and "not task.is_open" in source,
    ),
]

for label, ok in checks:
    print(("PASS" if ok else "FAIL") + ": " + label)

if not all(ok for _, ok in checks):
    raise SystemExit(
        "RESULT: EXECUTION STATE LIFECYCLE CLEANUP V1.1 VALIDATION FAILED"
    )

print(
    "RESULT: EXECUTION STATE LIFECYCLE CLEANUP V1.1 STRUCTURE VALID"
)
