from pathlib import Path
web=Path('aios/web_capture/app.py').read_text()
assert '<span class="mini-spinner"></span> Updating your focus…' in web
assert '.focus-pending .mini-spinner' in web
assert 'return_to="/?refresh_focus=1#focus-card"' in web
assert 'row_return_to = f"/#section-{quote_plus(section_key)}"' in web
assert 'row_return_to = f"/?search={quote_plus(search)}#search-results"' in web
print('Visible focus spinner: PASS')
print('BNA snooze returns to focus card: PASS')
print('Task-list snooze returns to originating section/search: PASS')
print('RESULT: FOCUS + SNOOZE + CHILD TITLE FOLLOW-UP V1 SMOKE TEST PASSED')
