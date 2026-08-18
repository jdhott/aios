from pathlib import Path

web = Path('aios/web_capture/app.py').read_text()
assert 'class="breakdown-row" draggable="true"' in web
assert 'class="breakdown-title" type="text"' in web
assert 'class="breakdown-trash"' in web
assert 'onclick="addBreakdownRow(this)"' in web
assert "titles.join(" in web
assert "list.insertBefore(dragging,after)" in web
assert 'submit_label="Accept Breakdown"' in web
assert 'submit_label="Save Breakdown"' in web
print('Editable rows render contract: PASS')
print('Drag/delete/add behavior wired: PASS')
print('Row order serializes through existing titles contract: PASS')
print('Proposal + existing breakdown share editor: PASS')
print('RESULT: BREAKDOWN LIST EDITOR V1 SMOKE TEST PASSED')
