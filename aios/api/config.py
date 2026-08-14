from __future__ import annotations

import os
from dataclasses import dataclass

API_SECURITY_VERSION = "cloud-run-api-v1.1-security"
LOCAL_ENVIRONMENTS = {"local", "development", "test"}
CLOUD_ENVIRONMENTS = {"cloudrun", "production"}

@dataclass(frozen=True)
class ApiSettings:
    environment: str
    platform_auth_required: bool
    local_auth_bypass: bool

    @property
    def auth_mode(self) -> str:
        if self.environment in CLOUD_ENVIRONMENTS:
            return "cloud_run_iam"
        if self.local_auth_bypass:
            return "local_explicit_bypass"
        return "local"

def _truthy(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}

def get_api_settings() -> ApiSettings:
    environment = os.getenv("AIOS_API_ENV", "local").strip().lower()
    if environment not in (LOCAL_ENVIRONMENTS | CLOUD_ENVIRONMENTS):
        raise RuntimeError(
            "AIOS_API_ENV must be one of: local, development, test, cloudrun, production"
        )
    local_auth_bypass = _truthy(os.getenv("AIOS_API_LOCAL_AUTH_BYPASS"))
    if environment in CLOUD_ENVIRONMENTS and local_auth_bypass:
        raise RuntimeError(
            "AIOS_API_LOCAL_AUTH_BYPASS cannot be enabled in cloudrun/production."
        )
    return ApiSettings(
        environment=environment,
        platform_auth_required=(environment in CLOUD_ENVIRONMENTS),
        local_auth_bypass=local_auth_bypass,
    )

def validate_runtime_environment() -> ApiSettings:
    settings = get_api_settings()
    if settings.environment in CLOUD_ENVIRONMENTS:
        if not os.getenv("K_SERVICE"):
            raise RuntimeError(
                "AIOS_API_ENV indicates Cloud Run/production but K_SERVICE is not present."
            )
        if not os.getenv("SUPABASE_URL"):
            raise RuntimeError(
                "SUPABASE_URL must be provided to the Cloud Run service."
            )
        if not (
            os.getenv("SUPABASE_SECRET_KEY")
            or os.getenv("SUPABASE_KEY")
        ):
            raise RuntimeError(
                "A Supabase server credential must be provided via "
                "SUPABASE_SECRET_KEY or SUPABASE_KEY."
            )
    return settings
