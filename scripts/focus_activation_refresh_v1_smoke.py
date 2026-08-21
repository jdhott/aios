import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from aios.focus_activation_refresh import (
    get_openai_client,
    resolve_focus_parent_task_id,
)


class FakeResult:
    def __init__(self, data):
        self.data = data


class FakeQuery:
    def __init__(self, store, table_name):
        self.store = store
        self.table_name = table_name
        self.filters = []

    def select(self, *_args, **_kwargs):
        return self

    def eq(self, key, value):
        self.filters.append((key, value))
        return self

    def limit(self, *_args, **_kwargs):
        return self

    def execute(self):
        rows = self.store.tables.get(self.table_name, [])
        matched = rows
        for key, value in self.filters:
            matched = [row for row in matched if row.get(key) == value]
        return FakeResult(matched[:1])


class FakeStore:
    def __init__(self, tables):
        self.tables = tables
        self.client = self

    def table(self, name):
        return FakeQuery(self, name)


parent_id = "parent-1"
child_id = "child-1"

store = FakeStore({
    "tasks": [
        {
            "id": child_id,
            "parent_task_id": parent_id,
            "generated_source": "focus_activation",
            "is_open": False,
            "is_done": True,
            "is_archived": False,
        },
        {
            "id": parent_id,
            "parent_task_id": None,
            "generated_source": None,
            "is_open": True,
            "is_done": False,
            "is_archived": False,
        },
    ]
})

assert resolve_focus_parent_task_id(store, child_id) == parent_id
assert resolve_focus_parent_task_id(store, parent_id) == parent_id

saved_key = os.environ.pop("OPENAI_API_KEY", None)
try:
    assert get_openai_client() is None
finally:
    if saved_key:
        os.environ["OPENAI_API_KEY"] = saved_key

print("Parent resolution from activation child: PASS")
print("OpenAI client absent without API key: PASS")
print("RESULT: FOCUS ACTIVATION REFRESH V1 SMOKE PASSED")
