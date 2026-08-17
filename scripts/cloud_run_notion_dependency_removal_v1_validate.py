#!/usr/bin/env python3
from pathlib import Path

root = Path(__file__).resolve().parents[1]
config = (root / "aios/job/config.py").read_text()
deploy = (root / "scripts/deploy_cloud_run_job.sh").read_text()
runtime = (root / "run_aios.py").read_text()
audit = (root / "core/storage/supabase_authority_audit.py").read_text()

checks = [
    ("job config does not require Notion token", '"NOTION_TOKEN"' not in config),
    ("job config does not require Notion IDs", "TASKS_DATABASE_ID" not in config and "BRAIN_DUMP_PAGE_ID" not in config and "NOTION_PROJECTS_DATABASE_ID" not in config),
    ("deployment does not inject Notion secret", "aios-notion-token" not in deploy and "NOTION_TOKEN=" not in deploy),
    ("deployment does not inject Notion IDs", "TASKS_DATABASE_ID=" not in deploy and "BRAIN_DUMP_PAGE_ID=" not in deploy and "NOTION_PROJECTS_DATABASE_ID=" not in deploy and "AIOS_DASHBOARD_BLOCK_ID=" not in deploy and "ARCHIVE_TOGGLE_BLOCK_ID=" not in deploy),
    ("runtime has explicit optional Notion boundary", "NOTION_RUNTIME_REQUIRED" in runtime),
    ("Supabase runtime uses optional Notion values", 'os.getenv("NOTION_TOKEN", "")' in runtime and 'os.getenv("TASKS_DATABASE_ID", "")' in runtime),
    ("legacy Notion runtime still fails fast", 'os.environ["NOTION_TOKEN"]' in runtime and 'os.environ["BRAIN_DUMP_PAGE_ID"]' in runtime),
    ("authority audit treats Notion mutation as unexpected", '"unexpected_notion"' in audit and "allowed_task_mirror" not in audit and "allowed_interface" not in audit),
]

failed = []
for label, ok in checks:
    print(("PASS" if ok else "FAIL") + f": {label}")
    if not ok:
        failed.append(label)

if failed:
    print("RESULT: CLOUD RUN NOTION DEPENDENCY REMOVAL V1 VALIDATION FAILED")
    raise SystemExit(1)

print("RESULT: CLOUD RUN NOTION DEPENDENCY REMOVAL V1 STRUCTURE VALID")
