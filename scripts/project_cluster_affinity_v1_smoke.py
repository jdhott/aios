import json

from aios import projects


class FakeResponse:
    def __init__(self, payload):
        self.output_text = json.dumps(payload)


class FakeResponses:
    def __init__(self):
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)

        return FakeResponse({
            "match": {
                "project_key": "P001",
                "confidence": 0.94,
                "reason": (
                    "The emerged tasks are implementation work "
                    "for the existing AIOS development project."
                ),
            }
        })


class FakeClient:
    def __init__(self):
        self.responses = FakeResponses()


active_project = {
    "id": "p1",
    "name": "AIOS System Development and Enhancement",
}

project_contexts = [{
    "project": active_project,
    "project_name": "AIOS System Development and Enhancement",
    "active": True,
    "member_titles": [
        "Improve AIOS dashboard project cognition",
        "Add project context to AIOS",
        "Improve task execution ranking",
    ],
}]

client = FakeClient()

project, confidence, reason, auto_match = (
    projects.find_existing_project_cluster_match(
        "AIOS Enhancement and Feature Implementation",
        [
            "Improve AIOS project proposal feedback",
            "Add project activation review UI",
            "Improve project emergence matching",
        ],
        project_contexts,
        client,
    )
)

assert project is active_project
assert confidence == 0.94
assert auto_match is True
assert "existing ACTIVE project" in reason
assert len(client.responses.calls) == 1

prompt = client.responses.calls[0]["input"]

assert "AIOS Enhancement and Feature Implementation" in prompt
assert "Improve project emergence matching" in prompt
assert "AIOS System Development and Enhancement" in prompt
assert "Improve AIOS dashboard project cognition" in prompt

print("Strong emerged cluster reuses active project: PASS")
print("Cluster tasks supplied to semantic matcher: PASS")
print("Existing project members supplied to semantic matcher: PASS")
print("Cluster matcher has explicit AI dependency: PASS")
print("RESULT: PROJECT CLUSTER AFFINITY V1 SMOKE TEST PASSED")
