from unittest.mock import patch

import aios.api.app as api
from aios.web_capture.app import _page


# ------------------------------------------------------------
# API action semantics
# ------------------------------------------------------------

calls = []


def fake_mark_not_now(store, task_id):
    calls.append(("mark", task_id))
    return {
        "id": task_id,
        "title": "Check RSVPs from invited guests",
        "is_open": False,
        "is_done": False,
        "activation_disposition": "not_now",
        "generated_source": "focus_activation",
    }


def fake_processor():
    calls.append(("processor", None))
    return {"status": "requested"}


with (
    patch.object(api, "_store", lambda: object()),
    patch.object(
        api,
        "mark_focus_activation_not_now",
        fake_mark_not_now,
    ),
    patch.object(
        api,
        "_request_processor_run",
        fake_processor,
    ),
):
    result = api.not_now_task_http("child-1")


assert ("mark", "child-1") in calls
assert ("processor", None) in calls

assert result["not_now"] is True
assert result["task"]["is_done"] is False
assert result["task"]["is_open"] is False
assert (
    result["task"]["activation_disposition"]
    == "not_now"
)

print("Not now marks disposition without completion: PASS")
print("Not now requests processor run: PASS")


# ------------------------------------------------------------
# Dashboard activation controls
# ------------------------------------------------------------

focus = {
    "id": "parent-1",
    "title": "Plan 90th birthday party for Mum",
    "execution_rank": 1,
    "execution_score": 36,
    "importance": "High Importance",
    "activation": {
        "id": "child-1",
        "title": "Check RSVPs from invited guests",
        "duration": "10 min",
        "is_just_do_it": True,
        "parent_task_id": "parent-1",
        "step_order": 3,
        "generated_source": "focus_activation",
    },
}

html = _page(
    tasks={
        "top5": [],
        "quick_wins": [],
        "today": [],
        "just_do_it": [],
    },
    focus=focus,
)

assert 'action="/tasks/child-1/complete"' in html
print("Complete action retained: PASS")

assert 'action="/tasks/child-1/not-now"' in html
assert ">Not now</button>" in html
print("Not now action renders: PASS")

assert 'action="/tasks/parent-1/not-now"' not in html
print("Not now applies only to activation child: PASS")

print(
    "RESULT: FOCUS ACTIVATION NOT NOW UI V1 "
    "SMOKE TEST PASSED"
)
