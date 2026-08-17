from pathlib import Path

root = Path(__file__).resolve().parents[1]
source = (root / "aios" / "web_capture" / "app.py").read_text()

checks = [
    ("search results have stable anchor", 'id="search-results"' in source),
    ("active search results detected", 'document.getElementById("search-results")' in source),
    ("search scroll uses scrollIntoView", 'activeSearchResults.scrollIntoView' in source),
    ("search scroll targets section start", 'block: "start"' in source),
    ("saved task scroll cleared for search", 'sessionStorage.removeItem(scrollKey)' in source),
    ("ordinary refresh still restores saved scroll", 'else {{\n        restoreScroll();' in source),
]

failed = False
for label, ok in checks:
    print(f"{'PASS' if ok else 'FAIL'}: {label}")
    failed = failed or not ok

if failed:
    raise SystemExit("RESULT: DASHBOARD SEARCH SCROLL V1 STRUCTURE INVALID")
print("RESULT: DASHBOARD SEARCH SCROLL V1 STRUCTURE VALID")
