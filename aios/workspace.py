"""Workspace tenancy helpers (Phase 1 foundation)."""

from __future__ import annotations

import os

# Deterministic default workspace created by migrations/20260821_workspace_tenancy_phase1_v1.sql
DEFAULT_WORKSPACE_ID = "00000000-0000-4000-8000-000000000001"
DEFAULT_WORKSPACE_SLUG = "default"


def default_workspace_id() -> str:
    """Return the active default workspace id (override via AIOS_DEFAULT_WORKSPACE_ID)."""
    value = os.getenv("AIOS_DEFAULT_WORKSPACE_ID", DEFAULT_WORKSPACE_ID).strip()
    return value or DEFAULT_WORKSPACE_ID
