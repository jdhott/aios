from __future__ import annotations
import os
from dataclasses import dataclass

CLOUD_RUN_JOB_RUNTIME_VERSION = "cloud-run-job-v1-scaffold"

REQUIRED_SECRET_ENV = (
    "SUPABASE_URL",
    "SUPABASE_SECRET_KEY",
    "OPENAI_API_KEY",
)

@dataclass(frozen=True)
class JobSettings:
    datastore: str
    inbox_source: str
    environment: str

def validate_job_environment() -> JobSettings:
    environment = os.getenv("AIOS_JOB_ENV", "local").strip().lower()
    datastore = os.getenv("AIOS_DATASTORE", "").strip().lower()
    inbox_source = os.getenv("AIOS_INBOX_SOURCE", "").strip().lower()

    if environment == "cloudrun":
        if not os.getenv("CLOUD_RUN_JOB"):
            raise RuntimeError("AIOS_JOB_ENV=cloudrun requires CLOUD_RUN_JOB.")
        if datastore != "supabase":
            raise RuntimeError("Cloud Run Job requires AIOS_DATASTORE=supabase.")
        if inbox_source != "supabase":
            raise RuntimeError("Cloud Run Job requires AIOS_INBOX_SOURCE=supabase.")

        missing = [name for name in REQUIRED_SECRET_ENV if not os.getenv(name)]
        if missing:
            raise RuntimeError(
                "Missing required secret environment variables: " + ", ".join(missing)
            )

    return JobSettings(
        datastore=datastore or "notion",
        inbox_source=inbox_source or "notion",
        environment=environment,
    )
