#!/usr/bin/env python3
"""Validate focus context loading feedback (UX #2)."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB = (ROOT / "aios" / "web_capture" / "app.py").read_text()

checks = [
    ("version marker", 'WEB_FOCUS_CONTEXT_LOADING_VERSION = "focus-context-loading-v1"' in WEB),
    ("save form class", 'class="focus-context-save-form"' in WEB),
    ("help form class", 'class="focus-context-help-form"' in WEB),
    ("answer form class", 'class="focus-context-answer-form"' in WEB),
    ("showFocusUpdating helper", "const showFocusUpdating = () =>" in WEB),
    ("coaching pending helper", "const showFocusContextCoachingPending" in WEB),
    ("async fetch submit", 'headers: { "X-Requested-With": "fetch" }' in WEB or '"X-Requested-With": "fetch"' in WEB),
    ("bind focus context forms", "bindFocusContextForm" in WEB),
    ("initFocusCard wires forms", ".focus-context-save-form, .focus-context-help-form, .focus-context-answer-form" in WEB),
    ("save button saving label", 'button.textContent = "Saving…"' in WEB),
    ("coaching pending copy", "Improving your context…" in WEB),
    ("poll after submit", "startFocusPolling({" in WEB and "refreshFocus: true" in WEB),
    ("disabled button styling", ".focus-context-save[disabled]" in WEB),
    ("about page marker", "Focus context loading" in WEB),
]

failed = [name for name, ok in checks if not ok]
for name, ok in checks:
    print(f"{'PASS' if ok else 'FAIL'}: {name}")

if failed:
    print("\nRESULT: FOCUS CONTEXT LOADING V1 VALIDATION FAILED")
    raise SystemExit(1)

print("\nRESULT: FOCUS CONTEXT LOADING V1 STRUCTURE VALID")
