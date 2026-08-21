#!/usr/bin/env python3
"""Validate global Brain Dump bottom sheet."""

from __future__ import annotations

from pathlib import Path

WEB = (Path(__file__).resolve().parents[1] / "aios" / "web_capture" / "app.py").read_text()

checks = [
    ("version marker", 'WEB_BRAIN_DUMP_SHEET_VERSION = "brain-dump-sheet-v1.2"' in WEB),
    ("sheet matches app width", "width: min(720px, calc(100% - 40px))" in WEB),
    ("column scrim", 'class="brain-dump-sheet-scrim"' in WEB),
    ("transparent backdrop", "background: transparent" in WEB and ".brain-dump-sheet-backdrop" in WEB),
    ("bottom sheet markup", 'class="brain-dump-sheet"' in WEB),
    ("capture fab", 'id="brain-dump-open"' in WEB),
    ("sheet submit endpoint", 'fetch("/capture/submit"' in WEB),
    ("sheet capture interface", "capture_sheet_v1" in WEB),
    ("keyboard shortcut", 'event.key.toLowerCase() === "b"' in WEB),
    ("shared draft key", "aios-capture-draft-v1" in WEB),
    ("included from bottom nav", "_brain_dump_sheet_html()" in WEB and "_brain_dump_sheet_script()" in WEB),
    ("more menu quick capture", "Quick capture" in WEB and "data-brain-dump-open" in WEB),
    ("more menu sheet item class", "bottom-nav-sheet-item" in WEB),
    ("dashboard button exclusions", ":not(.bottom-nav-sheet-item)" in WEB),
    ("dashboard card removed", 'id="brainDumpText"' not in WEB),
    ("submit accepts interface", "payload.get('capture_interface')" in WEB),
]

failed = [name for name, ok in checks if not ok]
for name, ok in checks:
    print(f"{'PASS' if ok else 'FAIL'}: {name}")

if failed:
    print("\nRESULT: BRAIN DUMP SHEET V1 VALIDATION FAILED")
    raise SystemExit(1)

print("\nRESULT: BRAIN DUMP SHEET V1 STRUCTURE VALID")
