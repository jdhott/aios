from pathlib import Path
api = Path('aios/api/app.py').read_text()
web = Path('aios/web_capture/app.py').read_text()
# Focused regression assertions: parent metadata travels with task-list payloads,
# while the pending manual-breakdown page actually reloads instead of assigning
# the same URL/hash (which browsers may treat as a no-op).
assert '.select("id,title")' in api
assert 'row["parent_title"] = parent_title_by_id.get(parent_id) or None' in api
assert "parent_html = (" in web
assert 'Part of: ' in web
pending = web[web.index('if breakdown_state == "pending"'):web.index('elif breakdown_state == "proposed"')]
assert 'window.location.reload();' in pending
assert 'window.location.href=' not in pending
print('Parent-task context enrichment: PASS')
print('Manual-breakdown pending auto-refresh: PASS')
print('RESULT: SUBTASK CONTEXT + BREAKDOWN REFRESH V1 SMOKE TEST PASSED')
