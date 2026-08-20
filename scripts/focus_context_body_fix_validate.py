from pathlib import Path
import importlib

s = Path('aios/api/app.py').read_text()
model_pos = s.index('class FocusContextSaveRequest(BaseModel):')
route_pos = s.index('@app.post("/tasks/{task_id}/focus-context"')
assert model_pos < route_pos
assert s.count('class FocusContextSaveRequest(BaseModel):') == 1
print('PASS: request model defined before route')

api = importlib.import_module('aios.api.app')
schema = api.app.openapi()
op = schema['paths']['/tasks/{task_id}/focus-context']['post']
assert 'requestBody' in op, op
query_names = {p.get('name') for p in op.get('parameters', []) if p.get('in') == 'query'}
assert 'request' not in query_names, op
print('PASS: focus context uses JSON request body')
print('PASS: request is not exposed as query parameter')
print('RESULT: FOCUS CONTEXT BODY FIX VALID')
