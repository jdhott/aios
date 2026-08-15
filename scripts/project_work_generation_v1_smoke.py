import json

from aios.project_work import generate_project_work


class FakeResponse:
    def __init__(self, data):
        self.output_text = json.dumps(data)


class FakeResponses:
    def __init__(self, data):
        self.data = data
        self.kwargs = None

    def create(self, **kwargs):
        self.kwargs = kwargs
        return FakeResponse(self.data)


class FakeClient:
    def __init__(self, data):
        self.responses = FakeResponses(data)


client = FakeClient({
    "state": "actionable",
    "tasks": [
        {
            "title": "Confirm the food plan for Mum's birthday party"
        },
        {
            "title": "Choose decorations for Mum's birthday party"
        },
    ],
})

result = generate_project_work(
    client,
    project_name="Plan 90th Birthday Party for Mum",
    project_anchor_title="Plan 90th birthday party for Mum",
    completed_work=[],
    open_work=[],
    completed_activation_steps=[
        "Write a list of close family and friends to invite.",
        "Draft a simple invitation message.",
    ],
)

assert result is not None
assert result["state"] == "actionable"
assert len(result["tasks"]) == 2

prompt = client.responses.kwargs["input"]

assert "Plan 90th Birthday Party for Mum" in prompt
assert "Write a list of close family and friends to invite." in prompt
assert "Draft a simple invitation message." in prompt
assert "without waiting" in prompt
assert "not tiny activation/JDI steps" in prompt

print("Project context supplied: PASS")
print("Completed activation history supplied: PASS")
print("Executable-now constraint supplied: PASS")
print("Project tasks parse: PASS")


waiting_client = FakeClient({
    "state": "waiting",
    "tasks": [],
})

waiting = generate_project_work(
    waiting_client,
    project_name="Plan 90th Birthday Party for Mum",
    project_anchor_title="Plan 90th birthday party for Mum",
    completed_work=[],
    open_work=[],
    completed_activation_steps=[
        "Send invitations to the guest list.",
    ],
)

assert waiting == {
    "state": "waiting",
    "tasks": [],
}

print("Waiting state parses without creating work: PASS")


duplicate_client = FakeClient({
    "state": "actionable",
    "tasks": [
        {
            "title": "Draft a simple invitation message."
        },
        {
            "title": "Confirm the cake plan"
        },
    ],
})

duplicate_result = generate_project_work(
    duplicate_client,
    project_name="Plan 90th Birthday Party for Mum",
    project_anchor_title="Plan 90th birthday party for Mum",
    completed_work=[],
    open_work=[],
    completed_activation_steps=[
        "Draft a simple invitation message.",
    ],
)

assert duplicate_result is not None
assert duplicate_result["tasks"] == [
    {"title": "Confirm the cake plan"}
]

print("Completed work duplicate rejected: PASS")


assert generate_project_work(
    None,
    project_name="Plan 90th Birthday Party for Mum",
) is None

print("Missing AI client fails closed: PASS")
print("RESULT: PROJECT WORK GENERATION V1 SMOKE TEST PASSED")
