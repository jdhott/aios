from aios.web_capture.app import _page

PARENT_ID = "parent-1"
CHILD_ID = "child-1"

focus = {
    "id": PARENT_ID,
    "title": "Plan 90th birthday party for Mum",
    "execution_rank": 1,
    "execution_score": 36,
    "importance": "High Importance",
    "starter_minutes": 10,
    "activation": {
        "id": CHILD_ID,
        "title": "Write a list of close family and friends to invite.",
        "is_just_do_it": True,
        "parent_task_id": PARENT_ID,
        "step_order": 1,
        "generated_source": "focus_activation",
        "duration": "10 min",
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

assert f'action="/tasks/{PARENT_ID}/complete"' not in html
print("Parent BNA has no completion action: PASS")

assert f'action="/tasks/{CHILD_ID}/complete"' in html
print("Activation child has completion action: PASS")

assert f'href="/tasks/{PARENT_ID}"' in html
print("Parent BNA task link preserved: PASS")

assert f'href="/tasks/{CHILD_ID}"' in html
print("Activation child task link preserved: PASS")

assert "Start here" in html
assert "Give it 10 min" in html
print("Activation guidance presentation preserved: PASS")

print("RESULT: FOCUS ACTIVATION UI V1 SMOKE TEST PASSED")
