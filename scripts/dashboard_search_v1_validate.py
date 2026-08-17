from pathlib import Path
root=Path(__file__).resolve().parents[1]
api=(root/'aios/api/app.py').read_text()
web=(root/'aios/web_capture/app.py').read_text()
checks=[
('search has dedicated result set','"search_results": search_results' in api),
('search returns before dashboard section selection', api.index('if clean_search:') < api.index('# Dashboard sections are independent views')),
('search results include all matched rows','search_results = sorted(' in api and 'rows,' in api[api.index('search_results = sorted('):api.index('search_results = sorted(')+120]),
('web renders dedicated Search Results','Search Results for' in web and '"search_results"' in web),
('search results preserve BNA matches','key not in {"today", "search_results"}' in web),
('clear search action exists','>Clear</a>' in web),
]
failed=False
for name,ok in checks:
 print(('PASS' if ok else 'FAIL')+': '+name); failed |= not ok
print('RESULT: DASHBOARD SEARCH V1 STRUCTURE '+('FAILED' if failed else 'VALID'))
raise SystemExit(1 if failed else 0)
