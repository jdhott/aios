from aios.project_work import (
    PROJECT_WORK_SOURCE,
    create_supabase_project_task,
    list_open_project_work,
)


class Result:
    def __init__(self, data):
        self.data = data


class FakeQuery:
    def __init__(self, client):
        self.client = client
        self.filters = []
        self.order_field = None
        self.insert_payload = None

    def select(self, *_args):
        return self

    def eq(self, field, value):
        self.filters.append((field, value))
        return self

    def order(self, field):
        self.order_field = field
        return self

    def insert(self, payload):
        self.insert_payload = dict(payload)
        return self

    def execute(self):
        if self.insert_payload is not None:
            row = {
                "id": f"task-{len(self.client.rows) + 1}",
                "created_at": "2026-08-15T16:00:00+00:00",
                **self.insert_payload,
            }
            self.client.rows.append(row)
            return Result([dict(row)])

        rows = [
            dict(row)
            for row in self.client.rows
            if all(
                row.get(field) == value
                for field, value in self.filters
            )
        ]

        if self.order_field:
            rows.sort(
                key=lambda row: (
                    row.get(self.order_field) is None,
                    row.get(self.order_field),
                )
            )

        return Result(rows)


class FakeClient:
    def __init__(self):
        self.rows = []

    def table(self, name):
        assert name == "tasks"
        return FakeQuery(self)


class FakeStore:
    def __init__(self):
        self.client = FakeClient()


PROJECT_ID = "project-1"

store = FakeStore()

task = create_supabase_project_task(
    store,
    title="Write birthday invitation",
    project_id=PROJECT_ID,
)

assert task["project_id"] == PROJECT_ID
assert task["parent_task_id"] is None
assert task["task_role"] is None
assert task["is_just_do_it"] is False
assert task["generated_source"] == PROJECT_WORK_SOURCE
assert task["is_open"] is True
assert task["is_done"] is False

print("Normal project task created: PASS")
print("Project relation persisted: PASS")
print("Project task is not JDI activation: PASS")
print("Project task has project_work provenance: PASS")

rows = list_open_project_work(
    store,
    PROJECT_ID,
)

assert len(rows) == 1
assert rows[0]["id"] == task["id"]

print("Open project work retrieval: PASS")

# Closed project work must not be returned.
store.client.rows[0]["is_open"] = False
store.client.rows[0]["is_done"] = True

assert list_open_project_work(
    store,
    PROJECT_ID,
) == []

print("Completed project work excluded: PASS")
print("RESULT: PROJECT WORK V1 SMOKE TEST PASSED")
