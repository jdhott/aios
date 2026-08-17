from pathlib import Path

root = Path(__file__).resolve().parents[1]
web = (root / 'aios' / 'web_capture' / 'app.py').read_text()
checks = [
    ('search results render open', "search_open = ' open' if key == \"search_results\" else ''" in web),
    ('search results ignore stored collapsed state', 'if (key === "search_results") {' in web and 'section.open = true;' in web),
    ('ordinary section persistence preserved', 'Object.prototype.hasOwnProperty.call(state, key)' in web),
]
failed=False
for name, ok in checks:
    print(f"{'PASS' if ok else 'FAIL'}: {name}")
    failed |= not ok
print('RESULT: DASHBOARD SEARCH EXPANDED V1 STRUCTURE VALID' if not failed else 'RESULT: DASHBOARD SEARCH EXPANDED V1 VALIDATION FAILED')
raise SystemExit(1 if failed else 0)
