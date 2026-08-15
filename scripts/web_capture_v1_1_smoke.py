#!/usr/bin/env python3
import base64
import os
from unittest.mock import patch

from fastapi.testclient import TestClient

import aios.web_capture.app as web


def basic(username, password):
    raw = f"{username}:{password}".encode()
    return {
        "Authorization": "Basic "
        + base64.b64encode(raw).decode()
    }


env = {
    "AIOS_WEB_USERNAME": "aios",
    "AIOS_WEB_PASSWORD": "test-password",
    "AIOS_API_URL": "https://aios-api.example.run.app",
}

assert web._split_brain_dump(
    "Task one\n\n Task two \nTask three"
) == [
    "Task one",
    "Task two",
    "Task three",
]

captured = []

with patch.dict(os.environ, env, clear=False), patch.object(
    web,
    "_capture_to_aios",
    lambda text: captured.append(text) or {
        "id": f"id-{len(captured)}",
        "status": "pending",
        "text": text,
    },
):
    with TestClient(web.app) as client:
        response = client.post(
            "/submit",
            headers=basic("aios", "test-password"),
            data={
                "text": (
                    "Replace smoke detector batteries\n"
                    "Call insurance adjuster\n"
                    "\n"
                    "Buy furnace filters"
                )
            },
            follow_redirects=False,
        )

assert response.status_code == 303, response.text
assert captured == [
    "Replace smoke detector batteries",
    "Call insurance adjuster",
    "Buy furnace filters",
]
assert "3+items+sent+to+AIOS." in response.headers["location"]

print("Line splitting trims whitespace: PASS")
print("Blank lines ignored: PASS")
print("Three lines create three API captures: PASS")
print("Batch success message reports item count: PASS")


calls = []

def sometimes_fails(text):
    calls.append(text)
    if text == "Second task":
        raise RuntimeError("synthetic")
    return {"id": "ok", "status": "pending", "text": text}

with patch.dict(os.environ, env, clear=False), patch.object(
    web,
    "_capture_to_aios",
    sometimes_fails,
):
    with TestClient(web.app) as client:
        response = client.post(
            "/submit",
            headers=basic("aios", "test-password"),
            data={"text": "First task\nSecond task\nThird task"},
            follow_redirects=False,
        )

assert response.status_code == 303
assert "2+item%28s%29+sent" in response.headers["location"]
assert "1+failed" in response.headers["location"]

print("Partial batch failure reports successes and failures: PASS")
print("RESULT: AIOS WEB CAPTURE V1.1 SMOKE TEST PASSED")
