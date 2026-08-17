import os
import core.storage.supabase_authority_audit as authority_audit
from core.storage.supabase_authority_audit import classify_mutation

def chk(m,u,p,e):
    got,_=classify_mutation(m,u,p)
    if got!=e:
        raise RuntimeError(f'{m} {u}: {got} != {e}')

def main():
    os.environ['TASKS_DATABASE_ID']='11111111-1111-1111-1111-111111111111'
    os.environ['PROJECTS_DATABASE_ID']='22222222-2222-2222-2222-222222222222'
    os.environ['NOTION_AI_LOG_DATABASE_ID']='33333333-3333-3333-3333-333333333333'

    pages='https://api.notion.com/v1/pages'
    chk('PATCH','https://api.notion.com/v1/blocks/x/children',{},'allowed_interface')
    chk('POST',pages,{'parent':{'database_id':os.environ['NOTION_AI_LOG_DATABASE_ID']}},'allowed_logging')
    chk('POST',pages,{'parent':{'database_id':os.environ['TASKS_DATABASE_ID']}},'allowed_task_mirror')
    chk('POST',pages,{'parent':{'database_id':os.environ['PROJECTS_DATABASE_ID']}},'unexpected_authoritative')
    chk('PATCH','https://api.notion.com/v1/pages/task1',{'properties':{}},'unexpected_authoritative')
    chk('POST',pages,{'parent':{'database_id':'55555555-5555-5555-5555-555555555555'}},'unclassified')

    authority_audit._EVENTS.clear()
    authority_audit._ENABLED=True
    authority_audit._record(
        'POST',
        'https://api.notion.com/v1/databases/33333333333333333333333333333333/query',
        {'page_size':8},
    )
    if authority_audit._EVENTS:
        raise RuntimeError(
            'Read-only Notion database query was incorrectly recorded as a mutation'
        )

    print('Database query POST exclusion: PASS')
    print('RESULT: SUPABASE AUTHORITY AUDIT SMOKE TEST PASSED')

if __name__=='__main__':
    main()
