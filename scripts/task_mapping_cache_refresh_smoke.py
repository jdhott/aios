#!/usr/bin/env python3
from types import SimpleNamespace

from aios.storage.task_metadata_writer import SupabaseTaskMetadataWriter
from aios.storage.task_lifecycle_writer import SupabaseTaskLifecycleWriter
from aios.storage.task_project_relation_writer import SupabaseProjectRelationWriter

NEW_NOTION_ID = "notion-new-task"
NEW_SUPABASE_ID = "supabase-new-task"

class ChangingTaskRepository:
    def __init__(self):
        self.calls = 0

    def get_all_tasks(self):
        self.calls += 1
        rows = [SimpleNamespace(legacy_notion_id="old-notion", id="old-supabase")]
        if self.calls >= 2:
            rows.append(SimpleNamespace(legacy_notion_id=NEW_NOTION_ID, id=NEW_SUPABASE_ID))
        return rows

class FakeQuery:
    def select(self, *args, **kwargs):
        return self
    def eq(self, *args, **kwargs):
        return self
    def limit(self, *args, **kwargs):
        return self
    def execute(self):
        return SimpleNamespace(data=[])

class FakeClient:
    def table(self, name):
        return FakeQuery()

class FakeStore:
    client = FakeClient()

def metadata_case():
    writer = SupabaseTaskMetadataWriter.__new__(SupabaseTaskMetadataWriter)
    writer.store = FakeStore()
    writer.repository = ChangingTaskRepository()
    writer._notion_to_supabase = None
    writer._ensure_map()
    assert NEW_NOTION_ID not in writer._notion_to_supabase
    assert writer._task_id(NEW_NOTION_ID) == NEW_SUPABASE_ID
    assert writer.repository.calls == 2

def lifecycle_case():
    writer = SupabaseTaskLifecycleWriter.__new__(SupabaseTaskLifecycleWriter)
    writer.store = FakeStore()
    writer.repository = ChangingTaskRepository()
    writer._notion_to_supabase = None
    writer._ensure_map()
    assert NEW_NOTION_ID not in writer._notion_to_supabase
    assert writer._task_id(NEW_NOTION_ID) == NEW_SUPABASE_ID
    assert writer.repository.calls == 2

def relation_case():
    writer = SupabaseProjectRelationWriter.__new__(SupabaseProjectRelationWriter)
    writer.store = FakeStore()
    writer.task_repository = ChangingTaskRepository()
    writer.project_repository = SimpleNamespace(get_all_projects=lambda: [])
    writer._task_map = None
    writer._project_legacy_map = {}
    writer._project_ids = set()
    writer._ensure_maps()
    assert NEW_NOTION_ID not in writer._task_map
    assert writer.resolve_task_id(NEW_NOTION_ID) == NEW_SUPABASE_ID
    assert writer.task_repository.calls == 2

metadata_case()
print("Metadata writer stale-cache recovery: PASS")
lifecycle_case()
print("Lifecycle writer stale-cache recovery: PASS")
relation_case()
print("Project relation writer stale-cache recovery: PASS")
print("RESULT: TASK MAPPING CACHE REFRESH SMOKE TEST PASSED")
