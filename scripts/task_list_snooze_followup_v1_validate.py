from pathlib import Path
api = Path('aios/api/app.py').read_text()
web = Path('aios/web_capture/app.py').read_text()
checks = [
    ('dashboard filters future-deferred tasks', 'actionable_rows = [' in api and 'not _is_future_defer_value(row.get("defer_until"))' in api),
    ('search remains full open-task lookup', 'if clean_search:' in api and 'search_results = _respect_breakdown_step_order' in api),
    ('top5 uses actionable rows', 'row for row in actionable_rows' in api),
    ('BNA actions are separate row columns', '.focus-parent-row {{ grid-template-columns:44px minmax(0,1fr) 44px 44px; }}' in web),
    ('BNA snooze is outside metadata/main block', "+ _task_snooze_control_html(focus_id, css_class=\"focus-snooze\")" in web and 'focus-parent-actions' not in web),
    ('Start Here completion gives immediate focus feedback', 'onsubmit="showFocusUpdating()"' in web and 'function showFocusUpdating()' in web),
]
failed=[]
for label, ok in checks:
    print(('PASS' if ok else 'FAIL') + ': ' + label)
    if not ok: failed.append(label)
if failed:
    raise SystemExit('RESULT: TASK LIST SNOOZE FOLLOW-UP V1 VALIDATION FAILED')
print('RESULT: TASK LIST SNOOZE FOLLOW-UP V1 STRUCTURE VALID')
