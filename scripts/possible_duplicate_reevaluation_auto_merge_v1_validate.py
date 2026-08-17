#!/usr/bin/env python3

from pathlib import Path
import ast


root = Path(__file__).resolve().parents[1]

run = (
    root / "run_aios.py"
).read_text()

service = (
    root / "aios/services/review_service.py"
).read_text()

api = (
    root / "aios/api/app.py"
).read_text()

web = (
    root / "aios/web_capture/app.py"
).read_text()


checks = [
    (
        "duplicate staging list exists",
        "pending_reevaluated_duplicates = []"
        in run,
    ),
    (
        "re-evaluated duplicate stages automatically",
        "→ duplicate; staged for automatic merge with"
        in run,
    ),
    (
        "auto merge notice persisted",
        '"auto_merge_notice"'
        in run,
    ),
    (
        "existing wording explicitly preserved",
        '"kept_wording": "existing"'
        in run,
    ),
    (
        "auto merge resolves link_existing",
        'action="link_existing"'
        in run,
    ),
    (
        "auto merge closes inbox lifecycle",
        "_mark_duplicate_review_inbox_processed("
        in run,
    ),
    (
        "failure leaves review pending",
        "Automatic duplicate merge failed; "
        "review remains pending:"
        in run,
    ),
    (
        "recent notice service exists",
        "def list_recent_auto_merge_notices("
        in service,
    ),
    (
        "notice expiry exists",
        "timedelta(minutes=10)"
        in service,
    ),
    (
        "recent notices API exists",
        '"/reviews/notices/recent"'
        in api,
    ),
    (
        "web fetches recent notices",
        "def _fetch_review_notices("
        in web,
    ),
    (
        "web renders automatic merge notice",
        "Merged automatically"
        in web,
    ),
    (
        "notice is session-scoped",
        "aios-auto-merge-notice-"
        in web,
    ),
]


for content in (
    run,
    service,
    api,
    web,
):
    ast.parse(content)


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
        "RESULT: AUTO-MERGE RE-EVALUATION "
        "VALIDATION FAILED: "
        + ", ".join(failed)
    )


print(
    "RESULT: POSSIBLE DUPLICATE RE-EVALUATION "
    "AUTO MERGE V1 STRUCTURE VALID"
)
