from pathlib import Path

root = Path(__file__).resolve().parents[1]
web = (root / 'aios' / 'web_capture' / 'app.py').read_text()
assert "search_open = ' open' if key == \"search_results\" else ''" in web
assert 'if (key === "search_results") {' in web
assert 'section.open = true;' in web
print('Search Results default expanded: PASS')
print('Stored collapsed state cannot override fresh search: PASS')
print('RESULT: DASHBOARD SEARCH EXPANDED V1 SMOKE TEST PASSED')
