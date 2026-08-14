#!/usr/bin/env python3
from aios.ingestion.models import InboxItem
from aios.ingestion.supabase_source import SupabaseInboxSource

class FakeRepository:
    def __init__(self):
        self.processed = []
    def get_pending_items(self):
        return [InboxItem(
            text="Test app capture",
            notes=["context"],
            source="brain_dump",
            source_item_id="inbox-row-1",
            source_type="inbox_item",
        )]
    def mark_processed(self, inbox_id):
        self.processed.append(inbox_id)
        return {"id": inbox_id, "status": "processed"}

repo = FakeRepository()
source = SupabaseInboxSource(repo)
items = source.list_pending_items()
assert len(items) == 1
assert items[0].source_item_id == "inbox-row-1"
source.remove_item(items[0])
assert repo.processed == ["inbox-row-1"]
print("Supabase inbox pending-item read: PASS")
print("Source-neutral InboxItem identity: PASS")
print("Processed lifecycle dispatch: PASS")
print("RESULT: APP SERVICE BOUNDARY V1 PHASE 1 SMOKE TEST PASSED")
