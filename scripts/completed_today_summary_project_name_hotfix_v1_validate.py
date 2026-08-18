from pathlib import Path
helper = Path('aios/daily_completion_summary.py').read_text()
checks = [
    ('projects use name column', 'table("projects").select("id,name")' in helper),
    ('project title mapping uses name value', 'str(row.get("name") or "").strip()' in helper),
    ('stale projects.title query removed', 'table("projects").select("id,title")' not in helper),
]
failed=False
for label, ok in checks:
    print(('PASS' if ok else 'FAIL') + ': ' + label)
    failed |= not ok
if failed:
    raise SystemExit('RESULT: COMPLETED TODAY SUMMARY PROJECT NAME HOTFIX V1 VALIDATION FAILED')
print('RESULT: COMPLETED TODAY SUMMARY PROJECT NAME HOTFIX V1 STRUCTURE VALID')
