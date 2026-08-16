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
            raise RuntimeError("Unexpected extra AI call")

        return FakeResponse(self.responses.pop(0))


class FakeClient:
    def __init__(self, responses):
        self.responses = FakeResponses(responses)


feedback = [{
    "title": (
        "Create and distribute a potluck sign-up sheet "
        "with broad dish categories"
    ),
    "feedback": (
        "Keep the task name to 75 characters or less. "
        "Do not distribute or send it yet. "
        "Just create the sign-up sheet with broad categories."
    ),
}]


# ------------------------------------------------------------
# Correct replacement follows binding feedback.
# ------------------------------------------------------------

replacement_title = (
    "Create a potluck sign-up sheet with broad dish categories"
)

assert len(replacement_title) <= 75

client = FakeClient([
    {
        "state": "actionable",
        "tasks": [{
            "title": replacement_title,
        }],
    },
    {
        "approved": ["C1"],
        "rejected": [],
    },
])

result = generate_project_work(
    client,
    project_name="Plan 90th Birthday Party for Mum",
    project_context=(
        "Small family-only gathering. Dinner is potluck. "
        "Invitations have been sent."
    ),
    project_anchor_title="Plan 90th birthday party for Mum",
    proposal_feedback=feedback,
)

assert result == {
    "state": "actionable",
    "tasks": [{
        "title": replacement_title,
    }],
}

generation_prompt = client.responses.calls[0]["input"]
validation_prompt = client.responses.calls[1]["input"]

assert "binding correction" in generation_prompt.lower()
assert "Do not distribute or send it yet" in generation_prompt
assert "75 characters or less" in generation_prompt
assert "substituting a synonym" in generation_prompt

assert "binding correction" in validation_prompt.lower()
assert "synonym workarounds" in validation_prompt
assert "75 characters" in validation_prompt

print("Latest feedback treated as binding correction: PASS")
print("Explicit forbidden-action feedback reaches generator: PASS")
print("Explicit length feedback reaches generator and validator: PASS")


# ------------------------------------------------------------
# Oversized title fails closed before validation.
# ------------------------------------------------------------

too_long = (
    "Create a detailed potluck sign-up sheet with broad dish categories "
    "and instructions for every family member"
)

assert len(too_long) > 75

client = FakeClient([
    {
        "state": "actionable",
        "tasks": [{"title": too_long}],
    },
])

result = generate_project_work(
    client,
    project_name="Test Project",
)

assert result == {
    "state": "waiting",
    "tasks": [],
}

assert len(client.responses.calls) == 1

print("Titles over 75 characters are rejected deterministically: PASS")


# ------------------------------------------------------------
# Exact rejected proposal cannot recur.
# ------------------------------------------------------------

client = FakeClient([
    {
        "state": "actionable",
        "tasks": [{
            "title": feedback[0]["title"],
        }],
    },
])

result = generate_project_work(
    client,
    project_name="Plan 90th Birthday Party for Mum",
    project_context="Dinner is potluck.",
    proposal_feedback=feedback,
)

assert result == {
    "state": "waiting",
    "tasks": [],
}

assert len(client.responses.calls) == 1

print("Rejected proposal cannot recur verbatim: PASS")

print(
    "RESULT: PROJECT WORK FEEDBACK GENERATION V1 "
    "SMOKE TEST PASSED"
)
