#!/usr/bin/env python3
import os
from unittest.mock import patch
from aios.job.config import validate_job_environment

env = {
    "AIOS_JOB_ENV": "cloudrun",
    "CLOUD_RUN_JOB": "aios-processor",
    "AIOS_DATASTORE": "supabase",
    "AIOS_INBOX_SOURCE": "supabase",
    "SUPABASE_URL": "https://example.supabase.co",
    "SUPABASE_SECRET_KEY": "test",
    "OPENAI_API_KEY": "test",
}

with patch.dict(os.environ, env, clear=True):
    settings = validate_job_environment()
    assert settings.datastore == "supabase"
    assert settings.inbox_source == "supabase"
    assert "NOTION_TOKEN" not in os.environ
    assert "TASKS_DATABASE_ID" not in os.environ


bad = dict(env)
bad["AIOS_DATASTORE"] = "notion"
with patch.dict(os.environ, bad, clear=True):
    try:
        validate_job_environment()
    except RuntimeError as exc:
        assert "AIOS_DATASTORE=supabase" in str(exc)
    else:
        raise RuntimeError("Notion datastore was incorrectly allowed")

missing = dict(env)
missing.pop("OPENAI_API_KEY")
with patch.dict(os.environ, missing, clear=True):
    try:
        validate_job_environment()
    except RuntimeError as exc:
        assert "OPENAI_API_KEY" in str(exc)
    else:
        raise RuntimeError("Missing OpenAI key was incorrectly allowed")

print("Cloud Run environment validation: PASS")
print("Supabase datastore enforcement: PASS")
print("Required Supabase/OpenAI secret enforcement: PASS")
print("No Notion production dependency: PASS")
print("RESULT: CLOUD RUN JOB V1 SMOKE TEST PASSED")
