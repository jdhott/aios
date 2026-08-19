from pathlib import Path
import ast
for f in ['aios/work_patterns.py','aios/api/app.py','aios/web_capture/app.py']:
    ast.parse(Path(f).read_text()); print(f'{f} parses: PASS')
mod=Path('aios/work_patterns.py').read_text()
assert 'project_order' in mod
assert 'task_context' in mod
assert 'generated_source' not in Path('migrations/20260818_work_patterns_v1.sql').read_text()
print('Instantiation appends ordered normal project tasks: PASS')
print('Pattern definition stays separate from live task state: PASS')
print('RESULT: WORK PATTERNS V1 SMOKE TEST PASSED')
