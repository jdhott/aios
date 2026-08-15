import json

from aios.focus_activation import generate_next_focus_activation


class FakeResponse:
    output_text = json.dumps({
        "title": "Choose two possible dates for the birthday party.",
        "minutes": 8,
    })


class FakeResponses:
    def create(self, **kwargs):
        self.kwargs = kwargs
        return FakeResponse()


class FakeClient:
    def __init__(self):
        self.responses = FakeResponses()


client = FakeClient()

result = generate_next_focus_activation(
    client,
    parent_title="Plan 90th birthday party for Mum",
    completed_steps=[
        "Write a list of close family and friends to invite.",
    ],
)

assert result is not None
assert result["title"] == "Choose two possible dates for the birthday party."
assert result["minutes"] == 10

prompt = client.responses.kwargs["input"]

assert "Plan 90th birthday party for Mum" in prompt
assert "Write a list of close family and friends to invite." in prompt
assert "Do not repeat" in prompt

print("Completed history supplied to generator: PASS")
print("Next activation parses: PASS")
print("Minutes normalize to JDI timebox: PASS")


duplicate_client = FakeClient()
duplicate_client.responses.create = lambda **kwargs: type(
    "Response",
    (),
    {
        "output_text": json.dumps({
            "title": "Write a list of close family and friends to invite.",
            "minutes": 10,
        })
    },
)()

duplicate = generate_next_focus_activation(
    duplicate_client,
    parent_title="Plan 90th birthday party for Mum",
    completed_steps=[
        "Write a list of close family and friends to invite.",
    ],
)

assert duplicate is None
print("Exact completed-step duplicate rejected: PASS")


assert generate_next_focus_activation(
    None,
    parent_title="Plan 90th birthday party for Mum",
    completed_steps=[],
) is None

print("Missing AI client fails closed: PASS")

print("RESULT: FOCUS ACTIVATION GENERATION V1 SMOKE TEST PASSED")
