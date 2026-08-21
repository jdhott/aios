#!/usr/bin/env python3
"""Validate review resolution confirmation toast (UX #4)."""

from __future__ import annotations

from pathlib import Path

WEB = (Path(__file__).resolve().parents[1] / "aios" / "web_capture" / "app.py").read_text()

checks = [
    ("version marker", 'WEB_REVIEW_TOAST_VERSION = "review-toast-v1"' in WEB),
    ("redirect helper", "def _reviews_redirect(" in WEB),
    ("toast css", ".review-toast {" in WEB),
    ("toast script", 'params.get("message")' in WEB and "review-toast" in WEB),
    ("reviews message param", 'params.get("message")' in WEB and "def _reviews_redirect(" in WEB),
    ("use existing toast", "Linked to existing task." in WEB and "Task wording updated." in WEB),
    ("clarification toast", 'message="Clarification accepted."' in WEB),
    ("delete toast", 'message="Task deleted."' in WEB),
    ("about page marker", "Review toast" in WEB),
]

failed = [name for name, ok in checks if not ok]
for name, ok in checks:
    print(f"{'PASS' if ok else 'FAIL'}: {name}")

if failed:
    print("\nRESULT: REVIEW TOAST V1 VALIDATION FAILED")
    raise SystemExit(1)

print("\nRESULT: REVIEW TOAST V1 STRUCTURE VALID")
