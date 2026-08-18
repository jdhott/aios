from pathlib import Path
import ast
source = Path('aios/daily_completion_summary.py').read_text()
ast.parse(source)
assert 'table("projects").select("id,name")' in source
assert 'table("projects").select("id,title")' not in source
assert 'table("tasks").select("id,title")' in source
print('Project enrichment uses Supabase projects.name: PASS')
print('Parent task enrichment still uses tasks.title: PASS')
print('Changed helper parses: PASS')
print('RESULT: COMPLETED TODAY SUMMARY PROJECT NAME HOTFIX V1 SMOKE TEST PASSED')
