from pathlib import Path
root=Path(__file__).resolve().parents[1]
run=(root/'run_aios.py').read_text()
assert 'inbox_source.remove_item(item)' in run
assert 'legacy Notion clarification runtime removed' in run
assert 'Supabase/web review authority configured' in run
assert 'legacy Notion dashboard runtime removed' in run
print('Supabase-only processor authority: PASS')
print('Optional capture lifecycle remains source-neutral: PASS')
print('RESULT: LEGACY NOTION RUNTIME CLEANUP V1 SMOKE TEST PASSED')
