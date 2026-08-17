from pathlib import Path

root = Path(__file__).resolve().parents[1]
source = (root / "aios" / "web_capture" / "app.py").read_text()

anchor = source.find('id="search-results"')
detect = source.find('document.getElementById("search-results")')
scroll = source.find('activeSearchResults.scrollIntoView')
restore = source.find('restoreScroll();', scroll)

assert anchor >= 0, "search results anchor missing"
assert detect >= 0, "search results detection missing"
assert scroll > detect, "search scroll must follow active-search detection"
assert 'if (activeSearchResults)' in source[detect:scroll], "search scroll must be conditional"
assert restore > scroll, "ordinary restore path must remain after search scroll path"

print("Search results anchor rendered: PASS")
print("Active search scrolls to results: PASS")
print("Non-search scroll restoration preserved: PASS")
print("RESULT: DASHBOARD SEARCH SCROLL V1 SMOKE TEST PASSED")
