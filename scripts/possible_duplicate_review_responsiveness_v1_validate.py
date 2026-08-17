from pathlib import Path

root = Path(__file__).resolve().parents[1]
api = (root / 'aios/api/app.py').read_text()
service = (root / 'aios/services/review_service.py').read_text()
web = (root / 'aios/web_capture/app.py').read_text()

checks = [
    ('create-new uses FastAPI background task', 'background_tasks.add_task(_request_processor_run)' in api),
    ('create-new no longer triggers processor inline', 'Create-new requested; processor trigger failed' not in api),
    ('durable create-anyway is hidden from pending reviews', 'requested_action' in service and 'create_anyway' in service and 'do not keep showing it as pending UI' in service),
    ('web still redirects immediately after accepted request', '_request_possible_duplicate_create_new' in web and 'url="/reviews"' in web),
]
failed=[]
for label, ok in checks:
    print(('PASS' if ok else 'FAIL') + ': ' + label)
    if not ok: failed.append(label)
if failed:
    print('RESULT: POSSIBLE DUPLICATE REVIEW RESPONSIVENESS V1 VALIDATION FAILED')
    raise SystemExit(1)
print('RESULT: POSSIBLE DUPLICATE REVIEW RESPONSIVENESS V1 STRUCTURE VALID')
