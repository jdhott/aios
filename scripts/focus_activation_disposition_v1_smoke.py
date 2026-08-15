import json

from aios.focus_activation import (
    FOCUS_ACTIVATION_SOURCE,
    generate_next_focus_activation,
    mark_focus_activation_not_now,
    snooze_focus_activation,
)


class Result:
    def __init__(self, data):
        self.data = data


class FakeQuery:
    def __init__(self, client):
        self.client = client
        self.filters = []
        self.update_payload = None
        self.limit_count = None

    def select(self, *_args):
        return self

    def eq(self, field, value):
        self.filters.append((field, value))
        return self

    def limit(self, count):
        self.limit_count = count
        return self

    def update(self, payload):
        self.update_payload = dict(payload)
        return self

    def execute(self):
        rows = [
            row for row in self.client.rows
            if all(
                row.get(field) == value
                for field, value in self.filters
            )
        ]

        if self.limit_count is not None:
            rows = rows[:self.limit_count]

        if self.update_payload is not None:
            for row in rows:
                row.update(self.update_payload)

        return Result([dict(row) for row in rows])


class FakeClient:
    def __init__(self, rows):
        self.rows = rows

    def table(self, name):
        assert name == "tasks"
        return FakeQuery(self)


class FakeStore:
    def __init__(self, rows):
        self.client = FakeClient(rows)


class FakeAIResponse:
    def __init__(self, data):
        self.output_text = json.dumps(data)


class FakeResponses:
    def __init__(self, data):
        self.data = data
        self.last_input = ""

    def create(self, **kwargs):
        self.last_input = kwargs["input"]
        return FakeAIResponse(self.data)


class FakeAIClient:
    def __init__(self, data):
        self.responses = FakeResponses(data)


# ------------------------------------------------------------
# Not now
# ------------------------------------------------------------

rows = [{
    "id": "step-1",
    "title": "Check RSVPs from invited guests",
    "generated_source": FOCUS_ACTIVATION_SOURCE,
    "is_open": True,
    "is_done": False,
    "is_archived": False,
    "activation_disposition": None,
    "defer_until": None,
}]

store = FakeStore(rows)

result = mark_focus_activation_not_now(
    store,
    "step-1",
)

assert result["activation_disposition"] == "not_now"
assert result["is_open"] is False
assert result["is_done"] is False

print("Not-now disposition persisted: PASS")
print("Not-now task remains incomplete: PASS")


# ------------------------------------------------------------
# Snooze
# ------------------------------------------------------------

rows = [{
    "id": "step-2",
    "title": "Check final RSVP count",
    "generated_source": FOCUS_ACTIVATION_SOURCE,
    "is_open": True,
    "is_done": False,
    "is_archived": False,
    "activation_disposition": None,
    "defer_until": None,
}]

store = FakeStore(rows)

result = snooze_focus_activation(
    store,
    "step-2",
    "2026-10-01T09:00:00-04:00",
)

assert result["defer_until"] == "2026-10-01T09:00:00-04:00"
assert result["is_open"] is False
assert result["is_done"] is False

print("Snooze date persisted: PASS")
print("Snoozed task remains incomplete: PASS")


# ------------------------------------------------------------
# Generator knows unavailable history
# ------------------------------------------------------------

ai = FakeAIClient({
    "title": "Write down three menu options for the party",
    "minutes": 10,
})

generated = generate_next_focus_activation(
    ai,
    parent_title="Plan 90th birthday party for Mum",
    completed_steps=[
        "Draft the invitation message",
        "Send invitations to the guest list",
    ],
    unavailable_steps=[
        "Check RSVPs from invited guests",
    ],
)

assert generated is not None
assert generated["title"] == "Write down three menu options for the party"

prompt = ai.responses.last_input

assert "Draft the invitation message" in prompt
assert "Send invitations to the guest list" in prompt
assert "Check RSVPs from invited guests" in prompt
assert "Unavailable / rejected activation steps" in prompt
assert "must not depend on waiting" in prompt

print("Completed history supplied to generator: PASS")
print("Unavailable history supplied to generator: PASS")
print("Executable-now constraint supplied: PASS")


# ------------------------------------------------------------
# Unavailable duplicate rejected
# ------------------------------------------------------------

duplicate_ai = FakeAIClient({
    "title": "Check RSVPs from invited guests",
    "minutes": 10,
})

duplicate = generate_next_focus_activation(
    duplicate_ai,
    parent_title="Plan 90th birthday party for Mum",
    completed_steps=[],
    unavailable_steps=[
        "Check RSVPs from invited guests",
    ],
)

assert duplicate is None

print("Unavailable-step duplicate rejected: PASS")

print(
    "RESULT: FOCUS ACTIVATION DISPOSITION V1 "
    "SMOKE TEST PASSED"
)
