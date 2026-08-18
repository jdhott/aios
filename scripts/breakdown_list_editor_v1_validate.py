from pathlib import Path

web = Path('aios/web_capture/app.py').read_text()
checks = {
    'shared breakdown list editor': 'def _breakdown_list_editor_html' in web,
    'drag handles rendered': 'breakdown-drag' in web and 'draggable="true"' in web,
    'inline task title editing': 'class="breakdown-title"' in web,
    'trash action rendered': 'breakdown-trash' in web,
    'add task action rendered': '+ Add task' in web,
    'proposal uses list editor': 'submit_label="Accept Breakdown"' in web,
    'existing breakdown uses list editor': 'submit_label="Save Breakdown"' in web,
    'drag reorder javascript': "addEventListener('dragover'" in web,
    'form serializes row order': 'syncBreakdownTitles' in web,
    'completed tasks remain separate': 'Completed subtasks are preserved as history' in web,
}
for label, ok in checks.items():
    print(f"{'PASS' if ok else 'FAIL'}: {label}")
    if not ok: raise SystemExit(1)
print('RESULT: BREAKDOWN LIST EDITOR V1 STRUCTURE VALID')
