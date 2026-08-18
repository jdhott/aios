from pathlib import Path
root=Path(__file__).resolve().parents[1]
run=(root/'run_aios.py').read_text()
web=(root/'aios/web_capture/app.py').read_text()
# Regression intent: the two real-world tasks that exposed v1 overreach are now explicit NO examples.
for title in ['Prepare the backyard for winter','Organize paperwork for the insurance claim']:
    pos=run.index('Task: '+title)
    nearby=run[pos:pos+180]
    assert 'Decision: no' in nearby,title
    print(title+': conservative example PASS')
assert 'Completed subtasks are preserved as history' in web
assert 'rewrite, remove, add, or reorder lines' in web
print('Existing breakdown edit safeguards: PASS')
assert '<span class="mini-spinner"></span> Updating your focus…' in web
print('BNA refresh spinner: PASS')
print('RESULT: BREAKDOWN V2 + EXISTING EDIT SMOKE TEST PASSED')
