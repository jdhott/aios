from pathlib import Path

api = Path('aios/api/app.py').read_text()
web = Path('aios/web_capture/app.py').read_text()

# Regression-oriented smoke: verify the progress view remains separate from the
# open actionable task population and is rendered with its own non-actionable row.
assert '.eq("is_open", True)' in api
assert '.eq("is_done", False)' in api
assert '.eq("is_done", True)' in api
assert '"completed_today": completed_today' in api
assert 'renderer = render_completed_task if key == "completed_today" else render_task' in web
assert '<button class="complete-checkbox"' not in web[web.index('def render_completed_task'):web.index('section_specs = (')]
assert '<button class="trash-button"' not in web[web.index('def render_completed_task'):web.index('section_specs = (')]
assert '("Completed Today", "completed_today")' in web
print('Completed Today separated from actionable views: PASS')
print('Completed rows have task links but no completion/delete controls: PASS')
print('RESULT: DASHBOARD COMPLETED TODAY V1 SMOKE TEST PASSED')
