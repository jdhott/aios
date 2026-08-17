from aios.web_capture.app import _page

tasks={'search_results':[
 {'id':'t1','title':'Buy replacement batteries for kitchen scale','importance':'Medium Importance'},
 {'id':'t2','title':'Replace kitchen scale batteries','execution_rank':1,'best_next_action':True},
]}
html=_page(tasks=tasks,search='kitchen scale',focus={'id':'t2','title':'Replace kitchen scale batteries'},review_count=0)
checks=[
 ('dedicated search heading','Search Results for “kitchen scale”' in html),
 ('ordinary match rendered','Buy replacement batteries for kitchen scale' in html),
 ('BNA match not removed from search results',html.count('Replace kitchen scale batteries') >= 2),
 ('clear search rendered','>Clear</a>' in html),
]
failed=False
for name,ok in checks:
 print(('PASS' if ok else 'FAIL')+': '+name); failed |= not ok
print('RESULT: DASHBOARD SEARCH V1 SMOKE TEST '+('FAILED' if failed else 'PASSED'))
raise SystemExit(1 if failed else 0)
