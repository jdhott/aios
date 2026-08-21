from pathlib import Path

web = Path('aios/web_capture/app.py').read_text()
start = web.index('def _task_snooze_control_html')
end = web.index('class BreakdownActionError', start)
helper = web[start:end]
assert "one_hour" in helper
assert "three_hours" in helper
assert "tomorrow" in helper
assert "three_days" in helper
assert "one_week" in helper
assert "pick_date" in helper
assert 'external_form_id' in helper
print('Shared snooze presets + external form mode: PASS')

page_start = web.index('def _page(')
page_end = web.index('@app.get("/projects"', page_start) if '@app.get("/projects"' in web[page_start:] else len(web)
page = web[page_start:page_end]
assert 'snooze_html = _task_snooze_control_html' in page
assert '_task_snooze_control_html(focus_id, css_class="focus-snooze")' in page
print('Dashboard rows + BNA use shared icon snooze: PASS')

project_start = web.index('def _project_detail_page')
project_end = web.index('def _possible_duplicate_new_task_page', project_start)
project = web[project_start:project_end]
assert 'project-snooze-' in project
assert 'css_class="project-task-snooze"' in project
assert 'external_form_id=snooze_form_id' in project
print('Project task rows use icon snooze without nested forms: PASS')

route = web[web.index('def snooze_task_web'):web.index('def delete_task_web')]
assert 'target = _safe_return_to(return_to)' in route
assert 'Task+snoozed.' in route
print('Snooze preserves list return target: PASS')
print('RESULT: TASK LIST SNOOZE V1 SMOKE TEST PASSED')
