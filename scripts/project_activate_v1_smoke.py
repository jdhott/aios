from unittest.mock import patch

import aios.api.app as api


calls = []


class FakeWriter:
    def update(
        self,
        *,
        project_ref_id,
        status=None,
        is_active=None,
    ):
        calls.append({
            "project_ref_id": project_ref_id,
            "status": status,
            "is_active": is_active,
        })

        return {
            "id": project_ref_id,
            "name": "Plan 90th Birthday Party for Mum",
            "status": status,
            "is_active": is_active,
        }


with patch.object(
    api,
    "get_project_lifecycle_writer",
    lambda: FakeWriter(),
):
    result = api.activate_project_http("project-1")


assert calls == [{
    "project_ref_id": "project-1",
    "status": "Active",
    "is_active": True,
}]

assert result["activated"] is True
assert result["project"]["status"] == "Active"
assert result["project"]["is_active"] is True

print("Canonical lifecycle writer used: PASS")
print("Status set to Active: PASS")
print("is_active set to True: PASS")
print("RESULT: PROJECT ACTIVATE V1 SMOKE TEST PASSED")
