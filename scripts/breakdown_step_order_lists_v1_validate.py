from pathlib import Path

api = Path('aios/api/app.py').read_text()
checks = [
    ('shared sibling-order helper exists', 'def _respect_breakdown_step_order' in api),
    ('dashboard task query includes step_order', 'parent_task_id,step_order' in api),
    ('search respects breakdown step order', 'search_results = _respect_breakdown_step_order' in api),
    ('Today respects breakdown step order', 'today_items = _respect_breakdown_step_order' in api),
    ('JDI respects breakdown step order', 'jdi_items = _respect_breakdown_step_order' in api),
    ('Quick Wins respects step order after residual selection', 'quick_wins = _respect_breakdown_step_order(quick_win_candidates[:5])' in api),
    ('project task query includes breakdown ordering fields', 'project_order,parent_task_id,step_order' in api),
    ('explicit project order remains stronger', 'skip_if_project_ordered=True' in api),
    ('Top 5 remains execution-rank ordered', 'key=lambda row: int(row.get("execution_rank"))' in api),
]
failed = False
for label, ok in checks:
    print(f"{'PASS' if ok else 'FAIL'}: {label}")
    failed |= not ok
if failed:
    raise SystemExit('RESULT: BREAKDOWN STEP ORDER LISTS V1 VALIDATION FAILED')
print('RESULT: BREAKDOWN STEP ORDER LISTS V1 STRUCTURE VALID')
