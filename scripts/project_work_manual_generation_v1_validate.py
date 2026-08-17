from pathlib import Path

root = Path(__file__).resolve().parents[1]
processor = (root / "aios/project_work_processor.py").read_text()
api = (root / "aios/api/app.py").read_text()
web = (root / "aios/web_capture/app.py").read_text()
migration = (root / "migrations/20260817_project_work_manual_generation_v1.sql").read_text()

checks = [
    ("manual generation request state is persisted", "work_generation_requested_at" in migration and "work_generation_state" in migration),
    ("generation state supports pending/actionable/waiting/failed", all(v in migration for v in ["'pending'", "'actionable'", "'waiting'", "'failed'"])),
    ("API exposes targeted generation request", '"/projects/{project_id}/work-proposals/generate"' in api),
    ("manual request triggers processor in background", "background_tasks.add_task(_request_processor_run)" in api),
    ("project detail exposes generation state", '"work_generation_state": project_row.get("work_generation_state")' in api),
    ("manual generation bypasses only open-work gate", "if open_work and not manual_requested:" in processor),
    ("project context remains generation input", "project_context=str(project.get(\"context\") or \"\")" in processor),
    ("open work remains generation input", "open_work=open_work" in processor),
    ("completed work remains generation input", "completed_work=completed_work" in processor),
    ("manual result state is persisted", "_finish_manual_generation" in processor),
    ("Project Detail exposes Generate Project Work", ">Generate Project Work</button>" in web),
    ("waiting result has explicit feedback", "No missing project work found." in web),
    ("pending result explains full-context audit", "project outcome, context, open work, and completed work" in web),
]

failed = False
for label, ok in checks:
    print(f"{'PASS' if ok else 'FAIL'}: {label}")
    failed = failed or not ok

if failed:
    raise SystemExit("RESULT: PROJECT WORK MANUAL GENERATION V1 VALIDATION FAILED")

print("RESULT: PROJECT WORK MANUAL GENERATION V1 STRUCTURE VALID")
