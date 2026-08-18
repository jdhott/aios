import ast
from pathlib import Path

source = Path('aios/api/app.py').read_text()
tree = ast.parse(source)
fn = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == '_respect_breakdown_step_order')
module = ast.Module(body=[fn], type_ignores=[])
ns = {}
exec(compile(module, '<helper>', 'exec'), ns)
order = ns['_respect_breakdown_step_order']

items = [
    {'id': 'x', 'title': 'Unrelated'},
    {'id': 'c2', 'title': 'Second', 'parent_task_id': 'p', 'step_order': 2},
    {'id': 'y', 'title': 'Other'},
    {'id': 'c1', 'title': 'First', 'parent_task_id': 'p', 'step_order': 1},
    {'id': 'c3', 'title': 'Third', 'parent_task_id': 'p', 'step_order': 3},
]
result = order(items)
ids = [row['id'] for row in result]
assert ids == ['x', 'c1', 'c2', 'c3', 'y'], ids
print('Sibling tasks grouped at first sibling and ordered by step_order: PASS')

project_items = [
    {'id': 'c2', 'title': 'Second', 'parent_task_id': 'p', 'step_order': 2, 'project_order': 1},
    {'id': 'c1', 'title': 'First', 'parent_task_id': 'p', 'step_order': 1, 'project_order': 2},
]
result = order(project_items, skip_if_project_ordered=True)
assert [row['id'] for row in result] == ['c2', 'c1']
print('Explicit project_order remains authoritative: PASS')

missing = [
    {'id': 'c2', 'title': 'B', 'parent_task_id': 'p', 'step_order': None},
    {'id': 'c1', 'title': 'A', 'parent_task_id': 'p', 'step_order': 1},
]
result = order(missing)
assert [row['id'] for row in result] == ['c1', 'c2']
print('Missing step_order falls behind numbered siblings: PASS')
print('RESULT: BREAKDOWN STEP ORDER LISTS V1 SMOKE TEST PASSED')
