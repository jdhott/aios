import json

from aios.project_work import generate_project_work


class FakeResponse:
    def __init__(self, data):
        self.output_text = json.dumps(data)


class FakeResponses:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if not self.responses:
            raise RuntimeError("No fake response remaining")
        return FakeResponse(self.responses.pop(0))


class FakeClient:
    def __init__(self, responses):
        self.responses = FakeResponses(responses)


# ------------------------------------------------------------
# Candidate generation + validation
# ------------------------------------------------------------

client = FakeClient([
    {
        "state": "actionable",
        "tasks": [
            {
                "title": "Plan the potluck dinner menu"
            },
            {
                "title": "Choose a party theme"
            },
        ],
    },
    {
        "approved": ["C1"],
        "rejected": [
            {
                "id": "C2",
                "reason": "No known project context establishes a party theme."
            }
        ],
    },
])

result = generate_project_work(
    client,
    project_name="Plan 90th Birthday Party for Mum",
    project_context=(
        "Small family-only gathering. Dinner is potluck. "
        "Invitations have already been sent."
    ),
    project_anchor_title="Plan 90th birthday party for Mum",
    completed_work=[],
    open_work=[],
    completed_activation_steps=[
        "Write a list of close family and friends to invite.",
        "Draft a simple invitation message.",
    ],
)

assert result == {
    "state": "actionable",
    "tasks": [
        {
            "title": "Plan the potluck dinner menu"
        }
    ],
}

assert len(client.responses.calls) == 2

generation_prompt = client.responses.calls[0]["input"]
validation_prompt = client.responses.calls[1]["input"]

assert "Small family-only gathering" in generation_prompt
assert "Dinner is potluck" in generation_prompt
assert "Treat the Known project context as authoritative" in generation_prompt

assert "Plan the potluck dinner menu" in validation_prompt
assert "Choose a party theme" in validation_prompt
assert "When uncertain, REJECT" in validation_prompt

print("Project context supplied to generator: PASS")
print("Candidate generation parses: PASS")
print("Grounding validation runs: PASS")
print("Unsupported candidate filtered out: PASS")


# ------------------------------------------------------------
# No candidates survive validation -> waiting
# ------------------------------------------------------------

client = FakeClient([
    {
        "state": "actionable",
        "tasks": [
            {
                "title": "Choose decorations for the party"
            },
        ],
    },
    {
        "approved": [],
        "rejected": [
            {
                "id": "C1",
                "reason": "Decorations are not established by known context."
            }
        ],
    },
])

result = generate_project_work(
    client,
    project_name="Plan 90th Birthday Party for Mum",
    project_context=(
        "Small family-only gathering. Dinner is potluck."
    ),
    project_anchor_title="Plan 90th birthday party for Mum",
)

assert result == {
    "state": "waiting",
    "tasks": [],
}

print("Zero validated candidates becomes waiting: PASS")


# ------------------------------------------------------------
# Generator itself may decide project is waiting
# ------------------------------------------------------------

client = FakeClient([
    {
        "state": "waiting",
        "tasks": [],
    },
])

result = generate_project_work(
    client,
    project_name="Plan 90th Birthday Party for Mum",
    project_context="Invitations sent. Waiting for RSVPs.",
)

assert result == {
    "state": "waiting",
    "tasks": [],
}

assert len(client.responses.calls) == 1

print("Generator waiting state avoids validation call: PASS")


# ------------------------------------------------------------
# Missing AI fails closed
# ------------------------------------------------------------

assert generate_project_work(
    None,
    project_name="Plan 90th Birthday Party for Mum",
) is None

print("Missing AI client fails closed: PASS")

print(
    "RESULT: PROJECT WORK GENERATION V1 "
    "SMOKE TEST PASSED"
)
