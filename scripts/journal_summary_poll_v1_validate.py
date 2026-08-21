#!/usr/bin/env python3
"""Validate journal summary polling (today's pending summary auto-refresh)."""

from __future__ import annotations

from pathlib import Path

WEB = (Path(__file__).resolve().parents[1] / "aios" / "web_capture" / "app.py").read_text()

checks = [
    ("journal version marker", 'WEB_DAILY_JOURNAL_VERSION = "daily-journal-v1.2"' in WEB),
    ("day panel view helper", "def _journal_day_panel_view(" in WEB),
    ("day panel api", '@app.get("/api/journal/{journal_date}/day-panel")' in WEB),
    ("summary root target", 'id="journal-summary-root"' in WEB),
    ("completed root target", 'id="journal-completed-root"' in WEB),
    ("journal poll script", "def _journal_poll_script(" in WEB),
    ("poll uses fingerprint", '"initialFingerprint"' in WEB and "journal-summary-root" in WEB),
    ("fast home nav marker", 'WEB_HOME_FAST_NAV_VERSION = "home-fast-nav-v1"' in WEB),
    ("home uses fast param", 'home_href = "/" if active == "home" else "/?fast=1"' in WEB),
    ("home shell cache", "aios-home-shell-cache-v1" in WEB),
]

failed = [name for name, ok in checks if not ok]
for name, ok in checks:
    print(f"{'PASS' if ok else 'FAIL'}: {name}")

if failed:
    print("\nRESULT: JOURNAL SUMMARY POLL V1 VALIDATION FAILED")
    raise SystemExit(1)

print("\nRESULT: JOURNAL SUMMARY POLL V1 STRUCTURE VALID")
