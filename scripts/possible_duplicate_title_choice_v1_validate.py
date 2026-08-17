#!/usr/bin/env python3

from pathlib import Path


root = Path(__file__).resolve().parents[1]

schema = (
    root / "aios/api/schemas.py"
).read_text()

api = (
    root / "aios/api/app.py"
).read_text()

web = (
    root / "aios/web_capture/app.py"
).read_text()


checks = [
    (
        "API schema has title_choice",
        "title_choice: str | None = None"
        in schema,
    ),
    (
        "API validates existing/new choices",
        '"existing", "new"'
        in api,
    ),
    (
        "API limits title choice to link_existing",
        "title_choice is only valid for link_existing"
        in api,
    ),
    (
        "API uses review subject for new wording",
        "review.subject_text"
        in api,
    ),
    (
        "API updates existing task title",
        '.update({"title": new_title})'
        in api,
    ),
    (
        "web sends title_choice",
        '"title_choice": title_choice'
        in web,
    ),
    (
        "web offers existing wording",
        "Use existing task"
        in web,
    ),
    (
        "web offers new wording",
        "Replace with new wording"
        in web,
    ),
    (
        "web offers keep separate",
        "Keep as separate tasks"
        in web,
    ),
    (
        "web sends existing choice",
        'value="existing"'
        in web,
    ),
    (
        "web sends new choice",
        'value="new"'
        in web,
    ),
]


failed = []

for label, passed in checks:
    print(
        f"{label}: "
        f"{'PASS' if passed else 'FAIL'}"
    )

    if not passed:
        failed.append(label)


if failed:
    raise SystemExit(
        "FAILED: " + ", ".join(failed)
    )


print(
    "RESULT: POSSIBLE DUPLICATE TITLE CHOICE V1 "
    "STRUCTURE VALID"
)
