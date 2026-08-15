from aios.project_anchor import (
    PROJECT_ANCHOR_ROLE,
    mark_project_anchor,
)


class Result:
    def __init__(self, data):
        self.data = data


class FakeQuery:
    def __init__(self, client):
        self.client = client
        self.filters = []
        self.limit_value = None
        self.update_payload = None

    def select(self, *_args):
        return self

    def eq(self, field, value):
        self.filters.append((field, value))
        return self

    def limit(self, value):
        self.limit_value = value
        return self

    def update(self, payload):
        self.update_payload = dict(payload)
        return self

    def execute(self):
        rows = [
            row
            for row in self.client.rows
            if all(
                row.get(field) == value
                for field, value in self.filters
            )
        ]

        if self.update_payload is not None:
            for row in rows:
                row.update(self.update_payload)
            return Result([dict(row) for row in rows])

        if self.limit_value is not None:
            rows = rows[:self.limit_value]

        return Result([dict(row) for row in rows])


class FakeClient:
    def __init__(self):
        self.rows = [{
            "id": "task-1",
            "title": "Plan 90th birthday party for Mum",
            "task_role": None,
        }]

    def table(self, name):
        assert name == "tasks"
        return FakeQuery(self)


class FakeStore:
    def __init__(self):
        self.client = FakeClient()


store = FakeStore()

result = mark_project_anchor(
    store,
    "task-1",
)

assert result["task_role"] == PROJECT_ANCHOR_ROLE
assert store.client.rows[0]["task_role"] == PROJECT_ANCHOR_ROLE
print("Project anchor role written: PASS")

again = mark_project_anchor(
    store,
    "task-1",
)

assert again["task_role"] == PROJECT_ANCHOR_ROLE
assert len(store.client.rows) == 1
print("Project anchor marking is idempotent: PASS")

print("RESULT: PROJECT ANCHOR V1 SMOKE TEST PASSED")
