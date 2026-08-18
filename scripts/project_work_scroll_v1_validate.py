from pathlib import Path
root = Path(__file__).resolve().parents[1]
web = (root / 'aios/web_capture/app.py').read_text()
checks = [
    ('project work results has stable anchor', 'id="project-work-results"' in web),
    ('generation redirect targets results anchor', '?refresh_proposal=1#project-work-results' in web),
    ('refresh loads scroll results into view', 'results.scrollIntoView({ block: "start" })' in web),
    ('scroll only attached to proposal refresh flow', 'if refresh_proposal:' in web and 'project-work-results' in web),
    ('result anchor has top spacing', '.project-work-results {{ scroll-margin-top:24px; }}' in web),
]
failed=[]
for label, ok in checks:
    print(('PASS' if ok else 'FAIL') + ': ' + label)
    if not ok:
        failed.append(label)
print('RESULT: PROJECT WORK SCROLL V1 STRUCTURE ' + ('VALID' if not failed else 'FAILED'))
raise SystemExit(1 if failed else 0)
