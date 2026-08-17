#!/usr/bin/env python3

from pathlib import Path

root = Path(__file__).resolve().parents[1]
run_aios = (root / "run_aios.py").read_text()
transitions = (
    root / "aios/review/possible_duplicate_transitions.py"
).read_text()
web = (root / "aios/web_capture/app.py").read_text()

card_start = web.index('<div class="review-label">Possible duplicate</div>')
card_end = web.index("for review in clarifications:", card_start)
card = web[card_start:card_end]

checks = [
    (
        "processor uses request-preserving payload refresh",
        "refresh_possible_duplicate_payload(" in run_aios,
    ),
    (
        "create-anyway request is preserved",
        'requested_action == "reevaluate"' in transitions
        and 'payload["requested_action"] = requested_action' in transitions,
    ),
    (
        "existing task is shown before new task",
        card.index("Existing task") < card.index("New task"),
    ),
    (
        "existing task links to task details",
        'href="/tasks/{candidate_id}?return_to=%2Freviews"' in card,
    ),
    (
        "new task links to review details",
        'possible-duplicate/new-task' in card
        and "def possible_duplicate_new_task_detail_web" in web,
    ),
    (
        "action labels explain consequences",
        "Use existing task" in web
        and "Replace with new wording" in web
        and "Keep as separate tasks" in web,
    ),
    (
        "keep-separate displays processing state",
        'requested_action == "create_anyway"' in web
        and "Creating separate task…" in web,
    ),
    (
        "pending separate creation auto-refreshes",
        "duplicate_creation_pending" in web
        and "or duplicate_creation_pending" in web,
    ),
]

failed = []
for label, passed in checks:
    print(f"{label}: {'PASS' if passed else 'FAIL'}")
    if not passed:
        failed.append(label)

if failed:
    raise SystemExit("FAILED: " + ", ".join(failed))

print("RESULT: POSSIBLE DUPLICATE KEEP-SEPARATE V2 STRUCTURE VALID")
