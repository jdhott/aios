#!/usr/bin/env python3
from unittest.mock import patch

from fastapi.testclient import TestClient
import aios.api.app as api_module

with patch.object(
    api_module,
    "_request_processor_run",
    lambda: {
        "status": "triggered",
        "triggered": True,
        "operation": "operations/test",
    },
):
    with TestClient(api_module.app) as client:
        response = client.post("/processing/request")

assert response.status_code == 202, response.text
assert response.json()["accepted"] is True
assert response.json()["status"] == "triggered"
print("Scheduled request endpoint accepts trigger: PASS")

with patch.object(
    api_module,
    "_request_processor_run",
    lambda: {
        "status": "coalesced",
        "triggered": False,
        "running": True,
        "trigger_pending": False,
    },
):
    with TestClient(api_module.app) as client:
        response = client.post("/processing/request")

assert response.status_code == 202, response.text
assert response.json()["accepted"] is True
assert response.json()["status"] == "coalesced"
print("Scheduled request safely coalesces with active processor: PASS")

with patch.object(
    api_module,
    "_request_processor_run",
    lambda: {
        "status": "failed",
        "triggered": False,
        "error": "synthetic",
    },
):
    with TestClient(api_module.app) as client:
        response = client.post("/processing/request")

assert response.status_code == 503
assert "processing remains requested" in response.json()["detail"]
print("Trigger failure surfaces 503 for Scheduler retry: PASS")

with patch.object(
    api_module,
    "_request_processor_run",
    lambda: {
        "status": "disabled",
        "triggered": False,
    },
):
    with TestClient(api_module.app) as client:
        response = client.post("/processing/request")

assert response.status_code == 503
print("Disabled trigger rejects scheduled request: PASS")
print("RESULT: SCHEDULED COMPATIBILITY TRIGGER V1 SMOKE TEST PASSED")
