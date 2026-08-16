from aios.project_work_proposals import (
    accept_project_work_proposal,
    dismiss_project_work_proposal,
    list_proposed_project_work,
    replace_project_work_proposals,
)


class Result:
    def __init__(self, data):
        self.data = data


class FakeQuery:
    def __init__(self, client):
        self.client = client
        self.filters = []
        self.update_payload = None
        self.insert_payload = None
        self.order_field = None

    def select(self, *_args):
        return self

    def eq(self, field, value):
        self.filters.append((field, value))
        return self

    def order(self, field):
        self.order_field = field
        return self

    def update(self, payload):
        self.update_payload = dict(payload)
        return self

    def insert(self, payload):
        self.insert_payload = dict(payload)
        return self

    def execute(self):
        if self.insert_payload is not None:
            row = {
                "id": f"proposal-{len(self.client.rows) + 1}",
                "created_at": f"2026-08-15T12:00:0{len(self.client.rows)}+00:00",
                "updated_at": None,
                "accepted_at": None,
                "dismissed_at": None,
                **self.insert_payload,
            }
            self.client.rows.append(row)
            return Result([dict(row)])

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

        result = [dict(row) for row in rows]

        if self.order_field:
            result.sort(
                key=lambda row: (
                    row.get(self.order_field) is None,
                    row.get(self.order_field),
                )
            )

        return Result(result)


class FakeClient:
    def __init__(self):
        self.rows = []

    def table(self, name):
        assert name == "project_work_proposals"
        return FakeQuery(self)


class FakeStore:
    def __init__(self):
        self.client = FakeClient()


store = FakeStore()
project_id = "project-1"

# Initial proposal set.
rows = replace_project_work_proposals(
    store,
    project_id=project_id,
    titles=[
        "Create a potluck sign-up list",
        "Confirm party room access",
    ],
)

assert len(rows) == 2
print("Initial proposals created: PASS")

first_ids = {
    row["title"]: row["id"]
    for row in rows
}

# Refresh: preserve one, dismiss one, add one.
rows = replace_project_work_proposals(
    store,
    project_id=project_id,
    titles=[
        "Create a potluck sign-up list",
        "Prepare family photo display",
    ],
)

assert len(rows) == 2

by_title = {
    row["title"]: row
    for row in rows
}

assert (
    by_title["Create a potluck sign-up list"]["id"]
    == first_ids["Create a potluck sign-up list"]
)

print("Unchanged proposal preserved: PASS")

dismissed = [
    row
    for row in store.client.rows
    if row["title"] == "Confirm party room access"
]

assert dismissed[0]["status"] == "dismissed"
assert dismissed[0]["dismissed_at"] is not None

print("Stale proposal dismissed: PASS")

new = next(
    row
    for row in rows
    if row["title"] == "Prepare family photo display"
)

print("New proposal inserted: PASS")

# Accept one.
accepted = accept_project_work_proposal(
    store,
    by_title["Create a potluck sign-up list"]["id"],
)

assert accepted["status"] == "accepted"
assert accepted["accepted_at"] is not None

print("Proposal acceptance persisted: PASS")

# Dismiss the other.
dismissed = dismiss_project_work_proposal(
    store,
    new["id"],
)

assert dismissed["status"] == "dismissed"
assert dismissed["dismissed_at"] is not None

print("Proposal dismissal persisted: PASS")

assert list_proposed_project_work(
    store,
    project_id,
) == []

print("Resolved proposals leave review queue: PASS")
print("RESULT: PROJECT WORK PROPOSALS V1 SMOKE TEST PASSED")
