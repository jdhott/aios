#!/usr/bin/env python3
"""Validate instant Brain Dump capture acknowledgment."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
api = (ROOT / "aios" / "api" / "app.py").read_text()
web = (ROOT / "aios" / "web_capture" / "app.py").read_text()

checks = [
    ("inbox capture defers processor", "background_tasks.add_task(_request_processor_run)" in api),
    ("inbox endpoint accepts background tasks", "background_tasks: BackgroundTasks" in api.split("def capture_inbox")[1][:400]),
    ("sheet instant ack helper", "ackCapture" in web),
    ("sheet shows captured checkmark", "Captured ✓" in web),
    ("sheet no sending spinner", "Sending…" not in web.split("_brain_dump_sheet_script")[1][:6000]),
    ("pwa instant captured status", web.count("Captured ✓") >= 2),
    ("version marker", 'WEB_BRAIN_DUMP_SHEET_VERSION = "brain-dump-sheet-v1.9-capture-ack"' in web),
    ("processor trigger version bumped", "cloud-processor-trigger-v1.1-inbox-deferred" in api),
]

failed = []
for label, ok in checks:
    print(f"{'PASS' if ok else 'FAIL'}: {label}")
    if not ok:
        failed.append(label)

if failed:
    raise SystemExit("RESULT: BRAIN DUMP CAPTURE ACK V1 VALIDATION FAILED")
print("RESULT: BRAIN DUMP CAPTURE ACK V1 VALID")
