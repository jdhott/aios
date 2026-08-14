from __future__ import annotations

import os

import google.auth
from google.auth.transport.requests import AuthorizedSession


CLOUD_RUN_JOB_TRIGGER_VERSION = "cloud-processor-trigger-v1"


class CloudRunJobTrigger:
    """Execute the configured Cloud Run Job using the service identity."""

    def __init__(
        self,
        *,
        project: str | None = None,
        region: str | None = None,
        job_name: str | None = None,
    ):
        self.project = (
            project
            or os.getenv("GOOGLE_CLOUD_PROJECT")
            or ""
        ).strip()
        self.region = (
            region
            or os.getenv(
                "AIOS_CLOUD_RUN_REGION",
                "northamerica-northeast1",
            )
        ).strip()
        self.job_name = (
            job_name
            or os.getenv(
                "AIOS_CLOUD_RUN_JOB",
                "aios-processor",
            )
        ).strip()

        if not self.project:
            raise RuntimeError(
                "GOOGLE_CLOUD_PROJECT is required to trigger the processor."
            )

    def trigger(self) -> dict:
        credentials, _ = google.auth.default(
            scopes=[
                "https://www.googleapis.com/auth/cloud-platform"
            ]
        )
        session = AuthorizedSession(credentials)

        url = (
            "https://run.googleapis.com/v2/"
            f"projects/{self.project}/locations/{self.region}/"
            f"jobs/{self.job_name}:run"
        )

        response = session.post(
            url,
            json={},
            timeout=30,
        )

        if not response.ok:
            raise RuntimeError(
                "Cloud Run Job trigger failed: "
                f"{response.status_code} {response.text}"
            )

        return response.json()
