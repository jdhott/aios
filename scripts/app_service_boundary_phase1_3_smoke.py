#!/usr/bin/env python3
from aios.storage.inbox_repository import InboxRepository
from aios.ingestion.supabase_source import SupabaseInboxSource


class FakeResponse:
    def __init__(self, data):
        self.data = data


class FakeQuery:
    def __init__(self, rows):
        self.rows = rows

    def select(self, *_):
        return self

    def eq(self, *_):
        return self

    def order(self, *_):
        return self

    def range(self, *_):
        return self

    def execute(self):
        return FakeResponse(self.rows)


class FakeClient:
    def __init__(self, rows):
        self.rows = rows

    def table(self, _):
        return FakeQuery(self.rows)


class FakeStore:
    def __init__(self, rows):
        self.client = FakeClient(rows)


native = {
    "id": "native-row",
    "text": "Native app capture",
    "notes": [],
    "source": "brain_dump",
    "source_item_id": None,
    "source_metadata": {
        "capture_interface": "app",
    },
}

shadow = {
    "id": "shadow-row",
    "text": "Check generator quote",
    "notes": [],
    "source": "notion",
    "source_item_id": "real-notion-block-id",
    "source_metadata": {
        "shadow": True,
        "source_type": "to_do",
        "source_container_id": "brain-dump-block",
    },
}

repo = InboxRepository(FakeStore([native, shadow]))
items = repo.get_pending_items()

assert len(items) == 1
assert items[0].text == "Native app capture"
assert items[0].source_item_id == "native-row"
assert items[0].inbox_row_id == "native-row"

mapped_shadow = repo.row_to_inbox_item(shadow)
assert mapped_shadow.source == "notion"
assert mapped_shadow.source_item_id == "real-notion-block-id"
assert mapped_shadow.inbox_row_id == "shadow-row"
assert mapped_shadow.source_type == "to_do"

class LifecycleRepo:
    def __init__(self):
        self.processed = []

    def mark_processed(self, row_id):
        self.processed.append(row_id)

source = SupabaseInboxSource(LifecycleRepo())
source.remove_item(mapped_shadow)
assert source.repository.processed == ["shadow-row"]

print("Shadow exclusion from capture ingestion: PASS")
print("External source identity preserved: PASS")
print("Supabase row identity preserved separately: PASS")
print("Lifecycle uses durable inbox_row_id: PASS")
print(
    "RESULT: APP SERVICE BOUNDARY PHASE 1.3 SMOKE TEST PASSED"
)
