"""Controlled DB smoke for native mirrorless Supabase task creation."""
from aios.storage.supabase_store import SupabaseStore
from aios.storage.task_creation_writer import SupabasePrimaryTaskCreator

def forbidden_notion(*args, **kwargs):
    raise AssertionError("Notion must not be called")

def main():
    store=SupabaseStore(); creator=SupabasePrimaryTaskCreator()
    title="AIOS temporary mirrorless creation smoke test"
    page=creator.create(task_title=title,is_jdi=False,is_urgent=False,is_important=False,due_date=None,manual_project="",effort="Small Effort",importance=None,status=None,notion_create_fn=forbidden_notion)
    task_id=page.get("_supabase_id")
    result=store.client.table("tasks").select("id, legacy_notion_id, title, effort").eq("id",task_id).limit(1).execute()
    rows=result.data or []
    if len(rows)!=1: raise RuntimeError("Temporary Supabase task not found")
    row=rows[0]
    if row.get("legacy_notion_id") is not None: raise RuntimeError("Mirrorless task unexpectedly has legacy Notion ID")
    if row.get("title")!=title or row.get("effort")!="Small Effort": raise RuntimeError("Create-time metadata mismatch")
    store.client.table("tasks").delete().eq("id",task_id).execute()
    check=store.client.table("tasks").select("id").eq("id",task_id).execute()
    if check.data: raise RuntimeError("Temporary row was not cleaned up")
    print("RESULT: MIRRORLESS SUPABASE TASK CREATION WRITE SMOKE PASSED")
if __name__=="__main__": main()
