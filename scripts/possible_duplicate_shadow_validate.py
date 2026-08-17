#!/usr/bin/env python3

from pathlib import Path
import ast


root = Path(__file__).resolve().parents[1]

run = (
    root / "run_aios.py"
).read_text()

repo = (
    root / "aios/storage/inbox_repository.py"
).read_text()


checks = [
    (
        "duplicate review helper exists",
        "def shadow_possible_duplicate_review("
        in run,
    ),
    (
        "native-first review row resolver exists",
        "def get_review_row_for_item("
        in repo,
    ),
    (
        "native plus legacy lookup exists",
        "def get_review_rows_for_item("
        in repo,
    ),
    (
        "new review uses native-first resolver",
        ".get_review_row_for_item(item)"
        in run,
    ),
    (
        "existing review lookup spans compatible rows",
        "def _find_open_possible_duplicate_review_for_item("
        in run,
    ),
    (
        "possible duplicate review is created",
        'review_type="possible_duplicate"'
        in run,
    ),
    (
        "payload carries candidate judgment",
        all(
            value in run
            for value in [
                '"candidate_task_title"',
                '"match_score"',
                '"confidence"',
                '"semantic_state"',
                '"semantic_reason"',
            ]
        ),
    ),
    (
        "fresh judgment clears reevaluation request",
        'payload.pop("requested_action", None)'
        in run,
    ),
    (
        "Supabase review authority marker exists",
        '"supabase_review_authority_v1"'
        in run,
    ),
    (
        "review write remains non-blocking",
        "[Possible Duplicate Shadow] Write failed:"
        in run,
    ),
]


ast.parse(run)
ast.parse(repo)

failed = []

for label, ok in checks:
    print(
        f"{'PASS' if ok else 'FAIL'}: "
        f"{label}"
    )

    if not ok:
        failed.append(label)


if failed:
    raise SystemExit(
        "RESULT: POSSIBLE DUPLICATE "
        "REVIEW OWNERSHIP VALIDATION FAILED: "
        + ", ".join(failed)
    )


print(
    "RESULT: POSSIBLE DUPLICATE "
    "REVIEW OWNERSHIP STRUCTURE VALID"
)
