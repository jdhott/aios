#!/usr/bin/env python3
from pathlib import Path
import ast
root=Path(__file__).resolve().parents[1]
run=(root/'run_aios.py').read_text(); trans=(root/'aios/review/possible_duplicate_transitions.py').read_text()
ast.parse(run); ast.parse(trans)
checks=[
('transition helper exists','def resolve_possible_duplicate_review(' in trans),
('three decisions supported',all(x in trans for x in ['"link_existing"','"create_anyway"','"ignore"'])),
('Supabase authority marker active','"authority": "supabase_review_authority_v1"' in run and '"authority": "notion_shadow_only"' not in run),
('pending review lookup exists','def _open_possible_duplicate_review(item):' in run),
('link_existing resolves','_resolve_possible_duplicate_now(match, "link_existing")' in run),
('ignore resolves','_resolve_possible_duplicate_now(match, "ignore")' in run),
('create_anyway stages','_stage_possible_duplicate_create_anyway(match)' in run),
('create_anyway post-create resolution','_resolve_staged_possible_duplicate_create_anyway(item, created_pages)' in run),
('Notion remains UI','inbox_review_ui.get_possible_duplicate_action(item)' in run),
]
for label,ok in checks: print(f"{'PASS' if ok else 'FAIL'}: {label}")
if not all(ok for _,ok in checks): raise SystemExit('RESULT: POSSIBLE DUPLICATE REVIEW AUTHORITY CUTOVER VALIDATION FAILED')
print('RESULT: POSSIBLE DUPLICATE REVIEW AUTHORITY CUTOVER STRUCTURE VALID')
