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


# These stand in for the legacy-shaped runtime task objects.
runtime_task_1 = {
    "id": "runtime-1",
    "properties": {"legacy": True},
}

runtime_task_2 = {
    "id": "runtime-2",
    "properties": {"legacy": True},
}

semantic_existing_tasks = [
    {
        "id": "runtime-1",
        "title": "Schedule appointment for car service",
        "original_task": runtime_task_1,
    },
    {
        "id": "runtime-2",
        "title": "Check mileage on Honda Civic",
        "original_task": runtime_task_2,
    },
]


def map_result(result):
    state = str(result.get("state") or "distinct")

    matched_surface = result.get("task") or {}
    matched_task = matched_surface.get("original_task")
    score = float(result.get("confidence") or 0.0)

    if state == "duplicate" and matched_task:
        return "matches", matched_task, score

    if state == "possible_duplicate" and matched_task:
        return "possible_matches", matched_task, score

    return "tasks_to_create", None, score


# ------------------------------------------------------------
# Exact duplicate
# ------------------------------------------------------------

client = FakeClient({"match": None})

result = judge_duplicate(
    client,
    task_title="Schedule appointment for car service",
    existing_tasks=semantic_existing_tasks,
)

lane, task, score = map_result(result)

assert lane == "matches"
assert task is runtime_task_1
assert score == 1.0
assert client.responses.calls == []

print("Exact duplicate maps to existing-task lane: PASS")


# ------------------------------------------------------------
# Semantic possible duplicate
# ------------------------------------------------------------

client = FakeClient({
    "match": {
        "task_key": "T01",
        "confidence": 0.85,
        "reason": (
            "Likely the same service-booking action, "
            "but vehicle identity is not explicit."
        ),
    }
})

result = judge_duplicate(
    client,
    task_title="Book the Honda Civic in for service",
    existing_tasks=semantic_existing_tasks,
)

lane, task, score = map_result(result)

assert lane == "possible_matches"
assert task is runtime_task_1
assert score == 0.85

print("Semantic uncertainty maps to review lane: PASS")


# ------------------------------------------------------------
# Distinct task
# ------------------------------------------------------------

client = FakeClient({"match": None})

result = judge_duplicate(
    client,
    task_title="Record Honda service expenses",
    existing_tasks=semantic_existing_tasks,
)

lane, task, score = map_result(result)

assert lane == "tasks_to_create"
assert task is None

print("Distinct action maps to new-task lane: PASS")


# ------------------------------------------------------------
# Preserve original runtime object
# ------------------------------------------------------------

assert (
    semantic_existing_tasks[0]["original_task"]
    is runtime_task_1
)

print("Original runtime task survives semantic boundary: PASS")

print(
    "RESULT: DUPLICATE DETECTION PIPELINE V1 "
    "SMOKE TEST PASSED"
)
