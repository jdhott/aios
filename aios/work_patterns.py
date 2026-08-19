from __future__ import annotations
from datetime import datetime, timezone
from typing import Any
from aios.project_work import create_supabase_project_task
from aios.storage.supabase_store import SupabaseStore

def list_work_patterns(store: SupabaseStore) -> list[dict[str, Any]]:
    patterns = store.client.table("work_patterns").select("*").order("name").execute().data or []
    ids = [str(r["id"]) for r in patterns if r.get("id")]
    steps = store.client.table("work_pattern_steps").select("*").in_("pattern_id", ids).order("step_order").execute().data or [] if ids else []
    by_pattern = {}
    for step in steps: by_pattern.setdefault(str(step.get("pattern_id")), []).append(dict(step))
    result=[]
    for row in patterns:
        item=dict(row); item["steps"]=by_pattern.get(str(row.get("id")),[]); item["step_count"]=len(item["steps"]); result.append(item)
    return result

def get_work_pattern(store: SupabaseStore, pattern_id: str) -> dict[str, Any] | None:
    rows=store.client.table("work_patterns").select("*").eq("id",pattern_id).limit(1).execute().data or []
    if not rows: return None
    item=dict(rows[0]); item["steps"]=list(store.client.table("work_pattern_steps").select("*").eq("pattern_id",pattern_id).order("step_order").execute().data or []); item["step_count"]=len(item["steps"]); return item

def save_work_pattern(store: SupabaseStore, *, pattern_id: str | None, name: str, context: str | None, steps: list[dict[str, Any]]) -> dict[str, Any]:
    name=str(name or "").strip(); normalized=[]
    if not name: raise ValueError("Pattern name is required.")
    for step in steps:
        title=str(step.get("title") or "").strip()
        if title: normalized.append({"title":title,"context":str(step.get("context") or "").strip() or None})
    if not normalized: raise ValueError("A work pattern needs at least one step.")
    if pattern_id:
        if not get_work_pattern(store,pattern_id): raise ValueError("Work pattern not found.")
        store.client.table("work_patterns").update({"name":name,"context":str(context or "").strip() or None,"updated_at":datetime.now(timezone.utc).isoformat()}).eq("id",pattern_id).execute()
        store.client.table("work_pattern_steps").delete().eq("pattern_id",pattern_id).execute()
    else:
        rows=store.client.table("work_patterns").insert({"name":name,"context":str(context or "").strip() or None}).execute().data or []
        if not rows: raise RuntimeError("Work pattern creation returned no row.")
        pattern_id=str(rows[0]["id"])
    store.client.table("work_pattern_steps").insert([{"pattern_id":pattern_id,"step_order":i,**step} for i,step in enumerate(normalized,1)]).execute()
    return get_work_pattern(store,pattern_id) or {}

def delete_work_pattern(store: SupabaseStore, pattern_id: str) -> None:
    if not get_work_pattern(store,pattern_id): raise ValueError("Work pattern not found.")
    store.client.table("work_patterns").delete().eq("id",pattern_id).execute()

def duplicate_work_pattern(store: SupabaseStore, pattern_id: str) -> dict[str, Any]:
    p=get_work_pattern(store,pattern_id)
    if not p: raise ValueError("Work pattern not found.")
    return save_work_pattern(store,pattern_id=None,name=f"{p['name']} copy",context=p.get("context"),steps=p.get("steps") or [])

def instantiate_pattern_for_project(store: SupabaseStore, *, project_id: str, steps: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not (store.client.table("projects").select("id").eq("id",project_id).limit(1).execute().data or []): raise ValueError("Project not found.")
    current=store.client.table("tasks").select("project_order").eq("project_id",project_id).eq("is_open",True).eq("is_done",False).eq("is_archived",False).execute().data or []
    max_order=max([int(r.get("project_order") or 0) for r in current] or [0]); created=[]
    for offset,step in enumerate(steps,1):
        title=str(step.get("title") or "").strip()
        if not title: continue
        task=create_supabase_project_task(store,title=title,project_id=project_id); update={"project_order":max_order+offset}
        context=str(step.get("context") or "").strip()
        if context: update["task_context"]=context
        rows=store.client.table("tasks").update(update).eq("id",task["id"]).execute().data or []; created.append(dict(rows[0]) if rows else task)
    return created
