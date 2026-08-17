#!/usr/bin/env python3

from aios.review.possible_duplicate_transitions import (
    refresh_possible_duplicate_payload,
)

create_requested = refresh_possible_duplicate_payload(
    {
        "requested_action": "create_anyway",
        "candidate_task_id": "old-task",
    },
    {
        "candidate_task_id": "fresh-task",
        "match_score": 0.75,
    },
)

assert create_requested["requested_action"] == "create_anyway"
assert create_requested["candidate_task_id"] == "fresh-task"
assert create_requested["match_score"] == 0.75
print("Keep-separate request survives duplicate refresh: PASS")

reevaluate_requested = refresh_possible_duplicate_payload(
    {
        "requested_action": "reevaluate",
        "candidate_task_id": "old-task",
    },
    {
        "candidate_task_id": "fresh-task",
        "match_score": 0.81,
    },
)

assert "requested_action" not in reevaluate_requested
assert reevaluate_requested["candidate_task_id"] == "fresh-task"
print("Satisfied re-evaluation request is cleared: PASS")

print("RESULT: POSSIBLE DUPLICATE KEEP-SEPARATE V2 SMOKE TEST PASSED")
