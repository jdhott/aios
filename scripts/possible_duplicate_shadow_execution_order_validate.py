#!/usr/bin/env python3
from __future__ import annotations
import ast
from pathlib import Path
root=Path(__file__).resolve().parents[1]
text=(root/'run_aios.py').read_text(); tree=ast.parse(text)
defs=[]; calls=[]
for node in ast.walk(tree):
    if isinstance(node,ast.FunctionDef) and node.name=='upsert_possible_duplicate_review': defs.append(node.lineno)
    if isinstance(node,ast.Call) and isinstance(node.func,ast.Name) and node.func.id=='upsert_possible_duplicate_review': calls.append(node.lineno)
checks=[
('review upsert helper definition exists',bool(defs)),
('review upsert helper has runtime call',bool(calls)),
('helper defined before first call',bool(defs and calls) and min(defs)<min(calls)),
('Supabase branch calls upsert','if AIOS_DATASTORE == "supabase":\n                upsert_possible_duplicate_review(match)' in text),
('Notion fallback is separate branch','elif inbox_review_ui is not None:' in text),
]
for label,ok in checks: print(f"{'PASS' if ok else 'FAIL'}: {label}")
if not all(ok for _,ok in checks): raise SystemExit('RESULT: POSSIBLE DUPLICATE REVIEW EXECUTION ORDER VALIDATION FAILED')
print('RESULT: POSSIBLE DUPLICATE REVIEW EXECUTION ORDER STRUCTURE VALID')
