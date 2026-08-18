from pathlib import Path
root = Path(__file__).resolve().parents[1]
api = (root / 'aios/api/app.py').read_text()
web = (root / 'aios/web_capture/app.py').read_text()
checks = [
    ('task detail reports existing breakdown children', 'has_breakdown_children' in api and '.eq("parent_task_id", task_id)' in api),
    ('web suppresses duplicate breakdown request when children exist', 'or has_breakdown_children' in web and 'already has breakdown subtasks' in web),
    ('API breakdown errors are surfaced to user', 'class BreakdownActionError' in web and 'body.get("detail")' in web),
    ('request still anchors to breakdown section', '#breakdown' in web),
    ('pending breakdown still auto-refreshes', 'Building proposed breakdown' in web and 'setTimeout' in web),
]
failed=[]
for label, ok in checks:
    print(f"{'PASS' if ok else 'FAIL'}: {label}")
    if not ok: failed.append(label)
if failed:
    raise SystemExit('RESULT: MANUAL BREAKDOWN RUNTIME FIX V1 VALIDATION FAILED')
print('RESULT: MANUAL BREAKDOWN RUNTIME FIX V1 STRUCTURE VALID')
