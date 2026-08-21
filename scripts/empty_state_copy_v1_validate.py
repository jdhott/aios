#!/usr/bin/env python3
"""Validate empty-state copy fixes (UX #3)."""

from __future__ import annotations

from pathlib import Path

WEB = (Path(__file__).resolve().parents[1] / "aios" / "web_capture" / "app.py").read_text()

checks = [
    ("version marker", 'WEB_EMPTY_STATE_COPY_VERSION = "empty-state-copy-v1"' in WEB),
    ("dashboard empty helper", "def _dashboard_tasks_empty_message" in WEB),
    ("reviews empty helper", "def _reviews_empty_message" in WEB),
    ("dashboard caught up copy", "You're all caught up. No open tasks in your lists right now." in WEB),
    ("dashboard search empty copy", "No tasks match your search." in WEB),
    ("dashboard uses helper", "_dashboard_tasks_empty_message(search=search)" in WEB),
    ("reviews caught up copy", "All caught up. Nothing needs your review right now." in WEB),
    ("reviews uses helper", "_reviews_empty_message()" in WEB),
    ("about page marker", "Empty-state copy" in WEB),
]

failed = [name for name, ok in checks if not ok]
for name, ok in checks:
    print(f"{'PASS' if ok else 'FAIL'}: {name}")

if failed:
    print("\nRESULT: EMPTY STATE COPY V1 VALIDATION FAILED")
    raise SystemExit(1)

print("\nRESULT: EMPTY STATE COPY V1 STRUCTURE VALID")
