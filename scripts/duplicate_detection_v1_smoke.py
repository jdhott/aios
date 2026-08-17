import json

from aios.duplicate_detection import judge_duplicate


class FakeResponse:
    def __init__(self, payload):
        self.output_text = json.dumps(payload)


class FakeResponses:
    def __init__(self, payload):
        self.payload = payload
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return FakeResponse(self.payload)


class FakeClient:
    def __init__(self, payload):
        self.responses = FakeResponses(payload)


existing = [
    {
        "id": "t1",
        "title": "Schedule appointment for Honda Civic service",
    },
    {
        "id": "t2",
        "title": "Check mileage on Honda Civic",
    },
    {
        "id": "t3",
        "title": "Call garage after service appointment",
    },
]


# Exact match requires no AI.
exact_client = FakeClient({"match": None})

result = judge_duplicate(
    exact_client,
    task_title="Schedule appointment for Honda Civic service",
    existing_tasks=existing,
)

assert result["state"] == "duplicate"
assert result["task"]["id"] == "t1"
assert result["confidence"] == 1.0
assert exact_client.responses.calls == []

print("Exact normalized match is deterministic: PASS")


# Different wording, same action.
duplicate_client = FakeClient({
    "match": {
        "task_key": "T01",
        "confidence": 0.96,
        "reason": "Both tasks mean booking the Honda service appointment.",
    }
})

result = judge_duplicate(
    duplicate_client,
    task_title="Book the Civic in for service",
    existing_tasks=existing,
)

assert result["state"] == "duplicate"
assert result["task"]["id"] == "t1"

print("Semantic same-action duplicate detected: PASS")


# Related but distinct action.
distinct_client = FakeClient({
    "match": None
})

result = judge_duplicate(
    distinct_client,
    task_title="Confirm mileage before booking Honda service",
    existing_tasks=existing,
)

assert result["state"] == "distinct"

print("Related but distinct action is not duplicate: PASS")


# Plausible but uncertain match enters review band.
review_client = FakeClient({
    "match": {
        "task_key": "T01",
        "confidence": 0.81,
        "reason": "Likely the same booking action, but wording leaves ambiguity.",
    }
})

result = judge_duplicate(
    review_client,
    task_title="Arrange Honda service",
    existing_tasks=existing,
)

assert result["state"] == "possible_duplicate"
assert result["task"]["id"] == "t1"
assert result["confidence"] == 0.81

print("Uncertain semantic match enters review band: PASS")

print("RESULT: DUPLICATE DETECTION V1 SMOKE TEST PASSED")
