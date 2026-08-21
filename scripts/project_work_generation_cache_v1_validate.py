#!/usr/bin/env python3
from pathlib import Path

root = Path(__file__).resolve().parents[1]
processor = (root / "aios/project_work_processor.py").read_text()
migration = (root / "migrations/20260821_project_work_generation_cache_v1.sql").read_text()

checks = [
    ("generation cache version marker", "PROJECT_WORK_GENERATION_CACHE_VERSION" in processor),
    ("generation key helper", "def project_work_generation_key(" in processor),
    ("persist generation key helper", "def _persist_generation_key(" in processor),
    ("reuse cached proposals", "Reusing cached proposals for:" in processor),
    ("loads stored generation key", "work_proposals_generation_key" in processor),
    ("manual generation bypasses cache", "if not manual_requested:" in processor),
    ("migration adds generation key column", "work_proposals_generation_key" in migration),
]

for label, ok in checks:
    print(f"{'PASS' if ok else 'FAIL'}: {label}")

if not all(ok for _, ok in checks):
    raise SystemExit("RESULT: PROJECT WORK GENERATION CACHE V1 VALIDATION FAILED")

print("RESULT: PROJECT WORK GENERATION CACHE V1 STRUCTURE VALID")
