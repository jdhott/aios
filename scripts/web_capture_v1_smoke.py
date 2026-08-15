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

with patch.dict(os.environ, env, clear=False):
    with TestClient(web.app) as client:
        r = client.get("/")
        assert r.status_code == 401

        r = client.get(
            "/",
            headers=basic("aios", "wrong"),
        )
        assert r.status_code == 401

        r = client.get(
            "/",
            headers=basic("aios", "test-password"),
        )
        assert r.status_code == 200
        assert "Submit to AIOS" in r.text

        with patch.object(
            web,
            "_capture_to_aios",
            lambda text: {
                "id": "12345678-abcd",
                "status": "pending",
                "text": text,
            },
        ):
            r = client.post(
                "/submit",
                headers=basic("aios", "test-password"),
                data={"text": "Buy milk"},
                follow_redirects=False,
            )
            assert r.status_code == 303
            assert "message=" in r.headers["location"]

print("Unauthenticated request rejected: PASS")
print("Wrong password rejected: PASS")
print("Authenticated brain dump page renders: PASS")
print("Submit uses PRG redirect and accepts capture: PASS")
print("RESULT: AIOS WEB CAPTURE V1 SMOKE TEST PASSED")
