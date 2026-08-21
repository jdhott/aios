from aios.web_capture.app import _page

tasks = {
    "top5": [],
    "quick_wins": [],
    "today": [],
    "just_do_it": [],
}

# Execution engine temporarily has no Rank 1.
html = _page(
    tasks=tasks,
    focus=None,
    refresh_focus=True,
    message="Task completed.",
)

assert "Updating your focus" in html
print("Missing-focus transition renders: PASS")

assert "startFocusPolling" in html
assert "__AIOS_FOCUS_POLL__" in html
assert '"maxAttempts": 15' in html
print("Missing-focus transition polls safely: PASS")


# Rank 1 is back, but processor has not created its child yet.
focus = {
    "id": "parent-1",
    "title": "Plan 90th birthday party for Mum",
    "execution_rank": 1,
    "execution_score": 36,
    "starter_step": "STALE GUIDANCE",
    "starter_minutes": 10,
    "activation": None,
    "activation_pending": False,
}

html = _page(
    tasks=tasks,
    focus=focus,
    refresh_focus=True,
)

assert "Finding your next step" in html
assert "STALE GUIDANCE" not in html
print("Returned-focus child wait renders: PASS")

assert "startFocusPolling" in html or "__AIOS_FOCUS_POLL__" in html
print("Returned-focus child wait continues polling: PASS")


# Real child has arrived: polling stops.
focus["activation"] = {
    "id": "child-1",
    "title": "Check RSVPs from the invited guests.",
    "duration": "10 min",
    "parent_task_id": "parent-1",
    "step_order": 3,
    "generated_source": "focus_activation",
}

html = _page(
    tasks=tasks,
    focus=focus,
    refresh_focus=True,
)

assert 'action="/tasks/child-1/complete"' in html
assert "Check RSVPs from the invited guests." in html
assert "Give it 10 min" in html
print("Completed transition renders activation child: PASS")

print("RESULT: FOCUS REFRESH TRANSITION V1 SMOKE TEST PASSED")
