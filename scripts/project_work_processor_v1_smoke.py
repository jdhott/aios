import json

from aios.project_work_processor import (
    refresh_project_work_proposals,
)


class Result:
    def __init__(self, data):
        self.data = data


class FakeQuery:
    def __init__(self, client, table_name):
        self.client = client
        self.table_name = table_name
        self.filters = []
        self.order_field = None
        self.order_desc = False
        self.limit_count = None
        self.insert_payload = None
        self.update_payload = None

    def select(self, *_args):
        return self

    def eq(self, field, value):
        self.filters.append((field, value))
        return self

    def order(self, field, desc=False):
        self.order_field = field
        self.order_desc = bool(desc)
        return self

    def limit(self, count):
        self.limit_count = int(count)
        return self

    def insert(self, payload):
        self.insert_payload = dict(payload)
        return self

    def update(self, payload):
        self.update_payload = dict(payload)
        return self

    def execute(self):
        rows = self.client.tables[self.table_name]

        if self.insert_payload is not None:
            row = {
                "id": f"{self.table_name}-{len(rows) + 1}",
                "created_at": "2026-08-15T20:00:00+00:00",
                "updated_at": None,
                "accepted_at": None,
                "dismissed_at": None,
                **self.insert_payload,
            }
            rows.append(row)
            return Result([dict(row)])

        matched = [
            row
            for row in rows
            if all(
                row.get(field) == value
                for field, value in self.filters
            )
        ]

        if self.update_payload is not None:
            for row in matched:
                row.update(self.update_payload)

            return Result([
                dict(row)
                for row in matched
            ])

        result = [
            dict(row)
            for row in matched
        ]

        if self.order_field:
            result.sort(
                key=lambda row: (
                    row.get(self.order_field) is None,
                    row.get(self.order_field),
                ),
                reverse=self.order_desc,
            )

        if self.limit_count is not None:
            result = result[:self.limit_count]

        return Result(result)


class FakeClient:
    def __init__(self):
        self.tables = {
            "projects": [
                {
                    "id": "project-1",
                    "name": "Plan 90th Birthday Party for Mum",
                    "status": "Active",
                    "is_active": True,
                    "context": (
                        "Small family-only gathering. "
                        "Dinner is potluck."
                    ),
                },
                {
                    "id": "project-2",
                    "name": "Project With Existing Work",
                    "status": "Active",
                    "is_active": True,
                    "context": "",
                },
            ],
            "tasks": [
                {
                    "id": "anchor-1",
                    "title": "Plan 90th birthday party for Mum",
                    "project_id": "project-1",
                    "task_role": "project_anchor",
                    "generated_source": None,
                    "is_open": True,
                    "is_done": False,
                    "is_archived": False,
                    "parent_task_id": None,
                    "activation_disposition": None,
                    "defer_until": None,
                },
                {
                    "id": "activation-1",
                    "title": "Draft invitation message",
                    "project_id": None,
                    "task_role": None,
                    "generated_source": "focus_activation",
                    "is_open": False,
                    "is_done": True,
                    "is_archived": False,
                    "parent_task_id": "anchor-1",
                    "step_order": 1,
                    "duration": "10 min",
                    "activation_disposition": None,
                    "defer_until": None,
                    "created_at": "2026-08-15T18:00:00+00:00",
                    "updated_at": None,
                    "completed_at": "2026-08-15T18:10:00+00:00",
                    "is_just_do_it": True,
                },
                {
                    "id": "anchor-2",
                    "title": "Second project",
                    "project_id": "project-2",
                    "task_role": "project_anchor",
                    "generated_source": None,
                    "is_open": True,
                    "is_done": False,
                    "is_archived": False,
                    "parent_task_id": None,
                    "activation_disposition": None,
                    "defer_until": None,
                },
                {
                    "id": "real-task-2",
                    "title": "Call supplier",
                    "project_id": "project-2",
                    "task_role": None,
                    "generated_source": None,
                    "is_open": True,
                    "is_done": False,
                    "is_archived": False,
                    "parent_task_id": None,
                    "activation_disposition": None,
                    "defer_until": None,
                },
            ],
            "project_work_proposals": [],
        }

    def table(self, name):
        return FakeQuery(
            self,
            name,
        )


class FakeStore:
    def __init__(self):
        self.client = FakeClient()


class FakeAIResponse:
    def __init__(self, data):
        self.output_text = json.dumps(data)


class FakeResponses:
    def __init__(self):
        self.calls = []
        self.responses = [
            # Candidate generation.
            {
                "state": "actionable",
                "tasks": [
                    {
                        "title": "Create a potluck sign-up list"
                    },
                    {
                        "title": "Choose a party theme"
                    },
                ],
            },
            # Strict validation.
            {
                "approved": ["C1"],
                "rejected": [
                    {
                        "id": "C2",
                        "reason": "No project context establishes a theme.",
                    }
                ],
            },
        ]

    def create(self, **kwargs):
        self.calls.append(kwargs)

        if not self.responses:
            raise RuntimeError(
                "Unexpected extra AI call"
            )

        return FakeAIResponse(
            self.responses.pop(0)
        )


class FakeAIClient:
    def __init__(self):
        self.responses = FakeResponses()


store = FakeStore()
client = FakeAIClient()

result = refresh_project_work_proposals(
    store,
    client,
)

assert len(result) == 1

birthday = result[0]

assert birthday["project_id"] == "project-1"
assert birthday["state"] == "actionable"
assert len(birthday["proposals"]) == 1

proposal = birthday["proposals"][0]

assert proposal["project_id"] == "project-1"
assert proposal["title"] == "Create a potluck sign-up list"
assert proposal["status"] == "proposed"

print("Validated project work stored as proposal: PASS")

assert len(client.responses.calls) == 2

generation_prompt = client.responses.calls[0]["input"]

assert "Small family-only gathering" in generation_prompt
assert "Dinner is potluck" in generation_prompt
assert "Draft invitation message" in generation_prompt

print("Project context and completed activation history supplied: PASS")

project_2_proposals = [
    row
    for row in store.client.tables["project_work_proposals"]
    if row.get("project_id") == "project-2"
]

assert project_2_proposals == []

print("Project with existing executable work skipped: PASS")

real_tasks = [
    row
    for row in store.client.tables["tasks"]
    if row.get("generated_source") == "project_work"
]

assert real_tasks == []

print("Processor creates proposals, not real tasks: PASS")

print(
    "RESULT: PROJECT WORK PROCESSOR V1 "
    "SMOKE TEST PASSED"
)
