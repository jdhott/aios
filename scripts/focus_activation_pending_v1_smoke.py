from aios.web_capture.app import _page

focus = {
    "id": "parent-1",
    "title": "Plan 90th birthday party for Mum",
    "execution_rank": 1,
    "execution_score": 36,
    "importance": "High Importance",

    # Old guidance deliberately remains present.
    "starter_step": "THIS STALE GUIDANCE MUST NOT RENDER",
    "starter_minutes": 10,

    "activation": None,
    "activation_pending": True,
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

assert "Finding your next step" in html
print("Pending state renders: PASS")

assert "THIS STALE GUIDANCE MUST NOT RENDER" not in html
print("Stale guidance suppressed: PASS")

assert "Give it 10 min" not in html
print("Stale timebox suppressed: PASS")

assert "setTimeout" in html
assert "2000" in html
print("Pending state schedules refresh: PASS")

assert "count < 10" in html
print("Refresh loop is bounded: PASS")

print("RESULT: FOCUS ACTIVATION PENDING V1 SMOKE TEST PASSED")
