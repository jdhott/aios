"""Controlled smoke for native Supabase parent/subtask creation."""
from aios.storage.supabase_store import SupabaseStore
from aios.storage.task_creation_writer import SupabasePrimaryTaskHierarchyCreator


def main():
    store = SupabaseStore()
    creator = SupabasePrimaryTaskHierarchyCreator()
    notion_called = False

    def forbidden_notion_create(*args, **kwargs):
        nonlocal notion_called
        notion_called = True
        raise RuntimeError('Notion must not be called for native hierarchy creation')

    def no_op_post_create(page, explicit_important):
        return page

    pages = creator.create_hierarchy(
        parent_title='AIOS temporary native hierarchy smoke parent',
        subtasks=['AIOS temporary native hierarchy child one', 'AIOS temporary native hierarchy child two'],
        is_jdi=False, is_urgent=False, is_important=False, due_date=None,
        manual_project='', post_create_fn=no_op_post_create,
        notion_create_fn=forbidden_notion_create,
    )
    ids = [page['_supabase_id'] for page in pages]
    try:
        if notion_called:
            raise RuntimeError('Notion callback was invoked')
        if len(pages) != 3:
            raise RuntimeError(f'Expected 3 compatibility pages; found {len(pages)}')
        response = store.client.table('tasks').select(
            'id,legacy_notion_id,parent_task_id,step_order,title'
        ).in_('id', ids).execute()
        rows = response.data or []
        if len(rows) != 3:
            raise RuntimeError(f'Expected 3 rows; found {len(rows)}')
        by_id = {row['id']: row for row in rows}
        parent_id, child_one_id, child_two_id = ids
        if any(row.get('legacy_notion_id') is not None for row in rows):
            raise RuntimeError('Native hierarchy unexpectedly has legacy Notion IDs')
        if by_id[parent_id].get('parent_task_id') is not None:
            raise RuntimeError('Parent unexpectedly has a parent')
        if by_id[child_one_id].get('parent_task_id') != parent_id or by_id[child_two_id].get('parent_task_id') != parent_id:
            raise RuntimeError('Child parent links are incorrect')
        if by_id[child_one_id].get('step_order') != 1 or by_id[child_two_id].get('step_order') != 2:
            raise RuntimeError('Child step order is incorrect')
        child_relation = pages[1]['properties']['Parent Task']['relation']
        if child_relation != [{'id': parent_id}]:
            raise RuntimeError('Compatibility parent relation is incorrect')
        if pages[2]['properties']['Step Order']['number'] != 2:
            raise RuntimeError('Compatibility step order is incorrect')
        print('PASS: native hierarchy created without Notion mirrors')
        print('PASS: parent_task_id and step_order persisted')
        print('PASS: compatibility hierarchy properties preserved')
        print('RESULT: MIRRORLESS SUPABASE HIERARCHY WRITE SMOKE PASSED')
    finally:
        for task_id in reversed(ids):
            store.client.table('tasks').delete().eq('id', task_id).execute()


if __name__ == '__main__':
    main()
