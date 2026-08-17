from pathlib import Path

writer = Path('aios/storage/task_creation_writer.py').read_text()
runtime = Path('run_aios.py').read_text()
checks = [
    ('hierarchy inserts native Supabase rows', '"legacy_notion_id": None' in writer and 'parent_task_id' in writer and 'step_order' in writer),
    ('hierarchy returns compatibility pages', 'SupabasePrimaryTaskCreator._compat_page(parent_row)' in writer and 'SupabasePrimaryTaskCreator._compat_page(child_row)' in writer),
    ('compatibility page carries parent relation', '"Parent Task"' in writer and '"Step Order"' in writer),
    ('hierarchy does not invoke Notion callback', 'del notion_create_fn, notion_rollback_fn' in writer),
    ('runtime does not supply Notion hierarchy creator', 'notion_create_fn=_create_notion_task_only' not in runtime[runtime.index('def create_breakdown_tasks'):runtime.index('def create_breakdown_tasks')+5000]),
    ('runtime still enriches hierarchy tasks', 'post_create_fn=post_create' in runtime),
    ('Supabase rollback remains for partial hierarchy failure', 'for task_id in reversed(created_supabase_ids)' in writer),
]
failed=False
for label, ok in checks:
    print(('PASS' if ok else 'FAIL') + ': ' + label)
    failed |= not ok
if failed:
    print('RESULT: MIRRORLESS BREAKDOWN HIERARCHY V1 VALIDATION FAILED')
    raise SystemExit(1)
print('RESULT: MIRRORLESS BREAKDOWN HIERARCHY V1 STRUCTURE VALID')
