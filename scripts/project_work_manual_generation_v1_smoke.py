from types import SimpleNamespace

import aios.project_work_processor as processor


class Query:
    def __init__(self, db, table):
        self.db = db
        self.table = table
        self.filters = []
        self.update_payload = None

    def select(self, *_args, **_kwargs):
        return self

    def eq(self, key, value):
        self.filters.append((key, value))
        return self

    def update(self, payload):
        self.update_payload = dict(payload)
        return self

    def execute(self):
        rows = [dict(r) for r in self.db[self.table]]
        for key, value in self.filters:
            rows = [r for r in rows if r.get(key) == value]

        if self.update_payload is not None:
            for row in self.db[self.table]:
                if all(row.get(k) == v for k, v in self.filters):
                    row.update(self.update_payload)
            rows = [dict(r) for r in self.db[self.table] if all(r.get(k) == v for k, v in self.filters)]

        return SimpleNamespace(data=rows)


class Client:
    def __init__(self):
        self.db = {
            "projects": [
                {
                    "id": "p-manual",
                    "name": "Manual Project",
                    "status": "Active",
                    "is_active": True,
                    "outcome": "Finish the project well",
                    "context": "Budget is fixed and venue is already chosen.",
                    "work_generation_requested_at": "2026-08-17T20:00:00+00:00",
                    "work_generation_completed_at": None,
                    "work_generation_state": "pending",
                },
                {
                    "id": "p-auto",
                    "name": "Automatic Project",
                    "status": "Active",
                    "is_active": True,
                    "outcome": "Finish another project",
                    "context": "",
                    "work_generation_requested_at": None,
                    "work_generation_completed_at": None,
                    "work_generation_state": None,
                },
            ],
            "tasks": [
                {
                    "id": "m-open", "title": "Already planned open task", "project_id": "p-manual",
                    "task_role": None, "generated_source": None, "is_open": True, "is_done": False,
                    "is_archived": False, "parent_task_id": None, "activation_disposition": None, "defer_until": None,
                },
                {
                    "id": "m-done", "title": "Already completed task", "project_id": "p-manual",
                    "task_role": None, "generated_source": None, "is_open": False, "is_done": True,
                    "is_archived": False, "parent_task_id": None, "activation_disposition": None, "defer_until": None,
                },
                {
                    "id": "a-open", "title": "Existing auto work", "project_id": "p-auto",
                    "task_role": None, "generated_source": None, "is_open": True, "is_done": False,
                    "is_archived": False, "parent_task_id": None, "activation_disposition": None, "defer_until": None,
                },
            ],
        }

    def table(self, name):
        return Query(self.db, name)


class Store:
    def __init__(self):
        self.client = Client()


store = Store()
captured = []

old_generate = processor.generate_project_work
old_feedback = processor.list_project_work_feedback
old_replace = processor.replace_project_work_proposals
old_activation = processor.list_focus_activation_children

try:
    def fake_generate(_client, **kwargs):
        captured.append(kwargs)
        return {"state": "waiting", "tasks": []}

    processor.generate_project_work = fake_generate
    processor.list_project_work_feedback = lambda *_args, **_kwargs: []
    processor.list_focus_activation_children = lambda *_args, **_kwargs: []
    processor.replace_project_work_proposals = lambda _store, *, project_id, titles: []

    result = processor.refresh_project_work_proposals(store, object())
finally:
    processor.generate_project_work = old_generate
    processor.list_project_work_feedback = old_feedback
    processor.replace_project_work_proposals = old_replace
    processor.list_focus_activation_children = old_activation

assert len(result) == 1, result
assert result[0]["project_id"] == "p-manual"
assert result[0]["manual"] is True
assert result[0]["state"] == "waiting"
print("Manual request bypasses open-work automatic gate: PASS")

assert len(captured) == 1
kwargs = captured[0]
assert kwargs["project_context"] == "Budget is fixed and venue is already chosen."
assert kwargs["open_work"] == ["Already planned open task"]
assert kwargs["completed_work"] == ["Already completed task"]
print("Context + open + completed work supplied to generator: PASS")

manual_row = next(r for r in store.client.db["projects"] if r["id"] == "p-manual")
assert manual_row["work_generation_state"] == "waiting"
assert manual_row["work_generation_completed_at"]
print("Manual generation result state persisted: PASS")

assert all(item["project_id"] != "p-auto" for item in result)
print("Automatic project with existing work remains conservative: PASS")

print("RESULT: PROJECT WORK MANUAL GENERATION V1 SMOKE TEST PASSED")
