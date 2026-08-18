from pathlib import Path
web = Path('aios/web_capture/app.py').read_text()
section = web[web.index('function wireProjectTaskRow'):web.index('document.addEventListener', web.index('function wireProjectTaskRow'))]
assert "title.addEventListener('input',remember)" in section
assert "const liveTitle=input?input.value" in section
assert "title:liveTitle.trim()" in section
print('Live inline rename tracked before Save: PASS')
print('Save payload uses current edited title: PASS')
print('RESULT: PROJECT TASK RENAME PERSISTENCE V1 SMOKE TEST PASSED')
