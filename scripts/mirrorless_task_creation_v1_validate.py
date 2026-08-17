"""Structural validation for Mirrorless Task Creation v1 Phase A."""
from pathlib import Path
root=Path(__file__).resolve().parents[1]
writer=(root/'aios/storage/task_creation_writer.py').read_text()
runtime=(root/'run_aios.py').read_text()
checks=[
 ("creator inserts directly into Supabase", '.table("tasks").insert(payload).execute()' in writer),
 ("new task legacy Notion ID is null", '"legacy_notion_id": None' in writer),
 ("creator does not invoke Notion callback", 'del notion_create_fn, notion_rollback_fn' in writer),
 ("creator returns native compatibility page", '"_source": "supabase"' in writer and '"_supabase_id": task_id' in writer),
 ("runtime computes effort before native creation", 'effort = classify_effort(task_title)' in runtime),
 ("runtime computes inferred importance before native creation", 'importance_result = infer_importance(' in runtime and 'importance=effective_importance' in runtime),
 ("runtime assigns clarification status directly", 'status = (' in runtime and 'CLARIFY_STATUS' in runtime),
 ("normal native creation no longer supplies Notion creator", 'notion_create_fn=_create_notion_task_only' not in runtime[runtime.index('if can_use_supabase_primary:'):runtime.index('return _create_notion_task_only', runtime.index('if can_use_supabase_primary:'))]),
 ("breakdown hierarchy is native Supabase", 'create_supabase_primary_hierarchy(' in runtime and 'notion_create_fn=_create_notion_task_only' not in runtime[runtime.index('def create_breakdown_tasks'):runtime.index('def create_breakdown_tasks')+5000]),
]
failed=[]
for label,ok in checks:
 print(f"{'PASS' if ok else 'FAIL'}: {label}")
 if not ok: failed.append(label)
if failed: raise SystemExit('RESULT: MIRRORLESS TASK CREATION V1 STRUCTURE VALIDATION FAILED')
print('RESULT: MIRRORLESS TASK CREATION V1 STRUCTURE VALID')
