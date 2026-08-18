from pathlib import Path
web=Path('aios/web_capture/app.py').read_text()
api=Path('aios/api/app.py').read_text()
assert '[PROJECT TASK TRACE]' not in web + api
assert 'zip(ids, titles)' in web
assert '"title": raw_title.strip()' in web
assert '.update({"title": title, "project_order": order, "updated_at": now})' in api
print('Trace logging removed while native rename path remains: PASS')
print('RESULT: PROJECT TASK TRACE CLEANUP V1 SMOKE TEST PASSED')
