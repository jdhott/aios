#!/usr/bin/env python3
from pathlib import Path
import ast

root = Path(__file__).resolve().parents[1]

app = (root / "aios/api/app.py").read_text()
runner = (root / "scripts/run_cloud_job.py").read_text()
coord = (root / "aios/processing/trigger_coordinator.py").read_text()
trigger = (root / "aios/processing/cloud_run_trigger.py").read_text()
migration = (
    root / "supabase/migrations/20260814_cloud_processor_trigger_v1.sql"
).read_text()
requirements = (root / "requirements-api.txt").read_text()

for text in (app, runner, coord, trigger):
    ast.parse(text)

checks = [
    ("API trigger marker", 'AIOS_CLOUD_PROCESSOR_TRIGGER_VERSION = "cloud-processor-trigger-v1"' in app),
    ("capture requests processing", "_request_processor_run()" in app),
    ("trigger failures preserve capture", "Trigger failed; capture remains pending" in app),
    ("coordinator uses atomic Supabase RPC", '.rpc(function_name, {})' in coord),
    ("Cloud Run v2 jobs.run endpoint", "run.googleapis.com/v2/" in trigger and ":run" in trigger),
    ("job overlap guard", "if not coordinator.begin_processing()" in runner),
    ("job reruns when capture arrives mid-run", "rerun_needed = coordinator.finish_cycle()" in runner),
    ("job failure releases stale running state", "coordinator.mark_failed()" in runner),
    ("SQL singleton state table", "create table if not exists public.aios_processor_state" in migration),
    ("SQL request function", "request_aios_processing()" in migration),
    ("SQL stale running recovery", "interval '30 minutes'" in migration),
    ("SQL stale trigger recovery", "interval '10 minutes'" in migration),
    ("google-auth API dependency", "google-auth" in requirements),
]

for label, ok in checks:
    print(f"{'PASS' if ok else 'FAIL'}: {label}")

if not all(ok for _, ok in checks):
    raise SystemExit("RESULT: CLOUD PROCESSOR TRIGGER V1 VALIDATION FAILED")

print("RESULT: CLOUD PROCESSOR TRIGGER V1 STRUCTURE VALID")
