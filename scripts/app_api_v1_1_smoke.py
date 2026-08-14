#!/usr/bin/env python3
import os
from unittest.mock import patch

from fastapi.testclient import TestClient
from aios.api.config import validate_runtime_environment
import aios.api.app as api_module

with patch.dict(
    os.environ,
    {
        "AIOS_API_ENV": "local",
        "AIOS_API_LOCAL_AUTH_BYPASS": "true",
    },
    clear=False,
):
    settings = validate_runtime_environment()
    assert settings.environment == "local"
    assert settings.auth_mode == "local_explicit_bypass"

with patch.dict(
    os.environ,
    {
        "AIOS_API_ENV": "cloudrun",
        "AIOS_API_LOCAL_AUTH_BYPASS": "true",
        "K_SERVICE": "aios-api",
        "SUPABASE_URL": "https://example.supabase.co",
        "SUPABASE_SECRET_KEY": "test",
    },
    clear=False,
):
    try:
        validate_runtime_environment()
    except RuntimeError as exc:
        assert "cannot be enabled" in str(exc)
    else:
        raise RuntimeError("Cloud Run incorrectly allowed local bypass")

with patch.dict(
    os.environ,
    {
        "AIOS_API_ENV": "cloudrun",
        "AIOS_API_LOCAL_AUTH_BYPASS": "false",
        "K_SERVICE": "aios-api",
        "SUPABASE_URL": "https://example.supabase.co",
        "SUPABASE_SECRET_KEY": "test",
    },
    clear=False,
):
    settings = validate_runtime_environment()
    assert settings.auth_mode == "cloud_run_iam"

with patch.dict(
    os.environ,
    {
        "AIOS_API_ENV": "local",
        "AIOS_API_LOCAL_AUTH_BYPASS": "true",
    },
    clear=False,
):
    with TestClient(api_module.app) as client:
        response = client.get("/health")
        assert response.status_code == 200
        body = response.json()
        assert body["environment"] == "local"
        assert body["auth_mode"] == "local_explicit_bypass"

print("Explicit local mode validation: PASS")
print("Cloud Run local-bypass rejection: PASS")
print("Cloud Run secret/config validation: PASS")
print("Health security metadata: PASS")
print("RESULT: CLOUD RUN API V1.1 SMOKE TEST PASSED")
