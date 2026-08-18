from pathlib import Path
web=Path('aios/web_capture/app.py').read_text()
writing=Path('aios/task_writing.py').read_text()
runtime=Path('run_aios.py').read_text()
checks=[
 ('dashboard spinner CSS', '.focus-pending .mini-spinner' in web and '@keyframes dashboard-spin' in web),
 ('BNA snooze preserves focus context', 'return_to="/?refresh_focus=1#focus-card"' in web),
 ('dashboard rows preserve section context', 'row_return_to = f"/#section-{quote_plus(section_key)}"' in web),
 ('search snooze preserves search context', '#search-results' in web),
 ('shared child-title hierarchy guidance', 'do not repeat that context in a child title' in writing),
 ('breakdown prompt reinforces 55-character target', '55-character title target as especially important for breakdown children' in runtime),
]
failed=[]
for name,ok in checks:
 print(('PASS' if ok else 'FAIL')+': '+name)
 if not ok: failed.append(name)
if failed: raise SystemExit(1)
print('RESULT: FOCUS + SNOOZE + CHILD TITLE FOLLOW-UP V1 STRUCTURE VALID')
