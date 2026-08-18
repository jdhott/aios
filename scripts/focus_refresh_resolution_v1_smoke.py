from pathlib import Path

api = Path('aios/api/app.py').read_text()
web = Path('aios/web_capture/app.py').read_text()

# Regression: a completed activation leaves history but no active child. That
# durable state must not be represented as "still generating" forever.
assert 'task["activation_pending"] = bool(' not in api
assert 'task["activation_history_exists"] = bool(activation_history)' in api
print('Completed activation history cannot hold focus pending forever: PASS')

# The browser polls for a bounded period and then removes the transient request
# flag, allowing the same BNA to render even if AI produced no next activation.
assert 'url.searchParams.delete("refresh_focus")' in web
assert 'window.location.replace(' in web
print('Focus refresh has bounded resolution fallback: PASS')

# Both pending presentations should use the same visible spinner treatment.
assert web.count('<span class="mini-spinner"></span>') >= 2
print('Focus and START HERE pending states both show spinner: PASS')

# Dashboard row snooze should preserve the exact viewport; focus snooze should
# deliberately return to the focus card instead.
assert 'document.querySelectorAll(".task-snooze-menu form")' in web
assert 'return_to="/?refresh_focus=1#focus-card"' in web
print('List scroll continuity and focus anchoring are distinct: PASS')

print('RESULT: FOCUS REFRESH RESOLUTION V1 SMOKE TEST PASSED')
