from pathlib import Path

web = Path('aios/web_capture/app.py').read_text()
checks = [
    ('shared snooze control exists', 'def _task_snooze_control_html' in web),
    ('snooze uses icon control', 'aria-label="Snooze task"' in web and '⏰' in web),
    ('dashboard task rows render snooze', 'snooze_html = _task_snooze_control_html' in web),
    ('project task rows render snooze', 'css_class="project-task-snooze"' in web),
    ('BNA uses shared snooze control', '_task_snooze_control_html(focus_id, css_class="focus-snooze")' in web),
    ('project snooze returns to project', 'name="return_to" value="{project_return}"' in web),
    ('snooze route accepts return_to', 'return_to: Annotated[str, Form()] = ""' in web[web.index('def snooze_task_web'):web.index('def delete_task_web')]),
    ('completed today stays without snooze', 'def render_completed_task' in web),
]
failed = False
for label, ok in checks:
    print(f"{'PASS' if ok else 'FAIL'}: {label}")
    failed |= not ok
if failed:
    raise SystemExit('RESULT: TASK LIST SNOOZE V1 STRUCTURE FAILED')
print('RESULT: TASK LIST SNOOZE V1 STRUCTURE VALID')
