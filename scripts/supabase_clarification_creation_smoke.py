"""Offline smoke for mirrorless Supabase clarification creation."""
from dataclasses import dataclass
from typing import Any
from aios.storage.task_creation_writer import SupabasePrimaryTaskCreator

@dataclass
class FakeResponse:
    data: list[dict[str, Any]]

class FakeTable:
    def __init__(self, state): self.state=state; self.payload=None
    def insert(self,payload): self.payload=dict(payload); return self
    def execute(self):
        self.state["insert_payload"]=self.payload
        return FakeResponse(data=[{"id":"supabase-clarify-1", **self.payload}])
class FakeClient:
    def __init__(self,state): self.state=state
    def table(self,name):
        assert name=="tasks"; return FakeTable(self.state)
class FakeStore:
    def __init__(self,state): self.client=FakeClient(state)

def forbidden_notion(*args, **kwargs):
    raise AssertionError("Notion must not be called for native Supabase creation")

def main():
    state={}
    creator=SupabasePrimaryTaskCreator.__new__(SupabasePrimaryTaskCreator)
    creator.store=FakeStore(state)
    page=creator.create(
        task_title="Clarify next action: Plan garden project",
        is_jdi=False,is_urgent=False,is_important=False,due_date=None,
        manual_project="Garden", effort="Low Effort",
        importance="Medium Importance", status="Needs Clarification",
        notion_create_fn=forbidden_notion, notion_rollback_fn=forbidden_notion,
    )
    payload=state["insert_payload"]
    checks=[
        ("native task has no legacy Notion ID", payload.get("legacy_notion_id") is None),
        ("clarification status written at insert", payload.get("status")=="Needs Clarification"),
        ("effort written at insert", payload.get("effort")=="Low Effort"),
        ("importance written at insert", payload.get("importance")=="Medium Importance"),
        ("suggested project written at insert", payload.get("suggested_project")=="Garden"),
        ("returned identity is native", page.get("id")=="supabase-clarify-1" and page.get("_supabase_id")=="supabase-clarify-1"),
        ("returned source is Supabase", page.get("_source")=="supabase"),
        ("compat properties preserve status", page["properties"]["Status"]["select"]["name"]=="Needs Clarification"),
    ]
    failed=[]
    for label,ok in checks:
        print(f"{label}: {'PASS' if ok else 'FAIL'}")
        if not ok: failed.append(label)
    if failed: raise SystemExit("RESULT: MIRRORLESS CLARIFICATION CREATION SMOKE FAILED")
    print("RESULT: MIRRORLESS CLARIFICATION CREATION SMOKE PASSED")
if __name__=="__main__": main()
