from __future__ import annotations
import os
from dataclasses import dataclass

CLOUD_RUN_JOB_RUNTIME_VERSION = "cloud-run-job-v1-scaffold"

REQUIRED_SECRET_ENV = (
    "SUPABASE_URL",
    "SUPABASE_SECRET_KEY",
    "OPENAI_API_KEY",
    "NOTION_TOKEN",
)

REQUIRED_ID_ENV = (
    "TASKS_DATABASE_ID",
    "BRAIN_DUMP_PAGE_ID",
    "NOTION_PROJECTS_DATABASE_ID",
    "NOTION_AI_LOG_DATABASE_ID",
    "AIOS_DASHBOARD_BLOCK_ID",
    "ARCHIVE_TOGGLE_BLOCK_ID",
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

        missing_ids = [name for name in REQUIRED_ID_ENV if not os.getenv(name)]
        if missing_ids:
            raise RuntimeError(
                "Missing required AIOS runtime IDs: " + ", ".join(missing_ids)
            )

    return JobSettings(
        datastore=datastore or "notion",
        inbox_source=inbox_source or "notion",
        environment=environment,
    )
