from pathlib import Path
root = Path(__file__).resolve().parents[1]
web = (root / 'aios/web_capture/app.py').read_text()
# Generation and both dialogue continuation redirects should retain the results anchor.
count = web.count('?refresh_proposal=1#project-work-results')
assert count >= 3, f'expected at least 3 anchored proposal redirects, found {count}'
print('Generate/continue redirects stay on Project Work results: PASS')
assert '<div id="project-work-results" class="project-work-results">' in web
print('Suggested Project Work has stable scroll target: PASS')
assert 'requestAnimationFrame(() => results.scrollIntoView({ block: "start" }))' in web
print('Refresh keeps spinner/result section in viewport: PASS')
print('RESULT: PROJECT WORK SCROLL V1 SMOKE TEST PASSED')
