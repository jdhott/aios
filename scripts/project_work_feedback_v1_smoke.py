from aios.project_work_proposals import (
    retry_project_work_proposal,
)


class Result:
    def __init__(self, data):
        self.data = data


class FakeQuery:
    def __init__(self, rows):
        self.rows = rows
        self.filters = []
        self.payload = None

    def update(self, payload):
        self.payload = dict(payload)
        return self

    def eq(self, field, value):
        self.filters.append((field, value))
        return self

    def execute(self):
        matched = [
            row
            for row in self.rows
            if all(
                row.get(field) == value
                for field, value in self.filters
            )
        ]

        for row in matched:
            row.update(self.payload or {})

        return Result([
            dict(row)
            for row in matched
        ])


class FakeClient:
    def __init__(self):
        self.rows = [{
            "id": "proposal-1",
            "project_id": "project-1",
            "title": "Assign potluck dishes to guests",
            "status": "proposed",
            "feedback": None,
        }]

    def table(self, name):
        assert name == "project_work_proposals"
        return FakeQuery(self.rows)


class FakeStore:
    def __init__(self):
        self.client = FakeClient()


store = FakeStore()

result = retry_project_work_proposal(
    store,
    "proposal-1",
    feedback=(
        "Guests should choose their own dishes. "
        "Use a sign-up mechanism instead of assigning dishes."
    ),
)

assert result["status"] == "dismissed"
assert result["feedback"].startswith(
    "Guests should choose their own dishes"
)
assert result["dismissed_at"]
assert result["updated_at"]

print("Try Again stores user feedback: PASS")
print("Try Again reuses dismissed lifecycle: PASS")

try:
    retry_project_work_proposal(
        store,
        "proposal-1",
        feedback="",
    )
    raise AssertionError("Empty feedback should fail")
except ValueError:
    pass

print("Try Again requires meaningful feedback: PASS")
print("RESULT: PROJECT WORK FEEDBACK V1 SMOKE TEST PASSED")
