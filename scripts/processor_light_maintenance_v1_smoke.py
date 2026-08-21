#!/usr/bin/env python3
from aios.processing.maintenance_policy import should_run_heavy_ai_maintenance


class Result:
    def __init__(self, data):
        self.data = data


class FakeQuery:
    def __init__(self, client, table_name):
        self.client = client
        self.table_name = table_name
        self.filters = []

    def select(self, *_args):
        return self

    def eq(self, field, value):
        self.filters.append(("eq", field, value))
        return self

    def in_(self, field, values):
        self.filters.append(("in", field, tuple(values)))
        return self

    def limit(self, count):
        self.limit_count = int(count)
        return self

    def execute(self):
        rows = self.client.tables.get(self.table_name, [])

        matched = []
        for row in rows:
            ok = True
            for op, field, value in self.filters:
                if op == "eq" and row.get(field) != value:
                    ok = False
                    break
                if op == "in" and row.get(field) not in value:
                    ok = False
                    break
            if ok:
                matched.append(dict(row))

        if getattr(self, "limit_count", None) is not None:
            matched = matched[: self.limit_count]

        return Result(matched)


class FakeClient:
    def __init__(self, tables):
        self.tables = tables

    def table(self, name):
        return FakeQuery(self, name)


class FakeStore:
    def __init__(self, tables):
        self.client = FakeClient(tables)


idle_store = FakeStore({"tasks": [], "projects": []})
assert should_run_heavy_ai_maintenance(
    inbox_items=[],
    store=idle_store,
    run_summary={"tasks_created": 0},
) is False

pending_store = FakeStore(
    {
        "tasks": [{"id": "task-1", "breakdown_state": "pending"}],
        "projects": [],
    }
)
assert should_run_heavy_ai_maintenance(
    inbox_items=[],
    store=pending_store,
) is True

activity_store = FakeStore({"tasks": [], "projects": []})
assert should_run_heavy_ai_maintenance(
    inbox_items=[],
    store=activity_store,
    run_summary={"tasks_created": 1},
) is True

print("Idle processor runs skip heavy AI maintenance: PASS")
print("Pending AI work and pipeline activity still force heavy maintenance: PASS")
print("RESULT: PROCESSOR LIGHT MAINTENANCE V1 SMOKE TEST PASSED")
