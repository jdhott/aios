#!/usr/bin/env python3
from pathlib import Path
import ast

root = Path(__file__).resolve().parents[1]
config = (root / "aios/job/config.py").read_text()
runner = (root / "scripts/run_cloud_job.py").read_text()
dockerfile = (root / "Dockerfile.cloudrun-job").read_text()
deploy = (root / "scripts/deploy_cloud_run_job.sh").read_text()
cloudbuild = (root / "cloudbuild.job.yaml").read_text()

for text in (config, runner):
    ast.parse(text)

checks = [
    ("job config exists", "def validate_job_environment(" in config),
    ("Supabase datastore enforced", "AIOS_DATASTORE=supabase" in config),
    ("Supabase inbox enforced", "AIOS_INBOX_SOURCE=supabase" in config),
    ("Supabase secrets required", '"SUPABASE_URL"' in config and '"SUPABASE_SECRET_KEY"' in config),
    ("OpenAI secret required", '"OPENAI_API_KEY"' in config),
    ("Notion token required", '"NOTION_TOKEN"' in config),
    ("runner executes run_aios.py", "runpy.run_path(" in runner and "run_aios.py" in runner),
    ("full requirements used", "requirements.txt" in dockerfile and "requirements-api.txt" not in dockerfile),
    ("Python 3.14 image", "python:3.14-slim" in dockerfile),
    ("Cloud Build job Dockerfile", "Dockerfile.cloudrun-job" in cloudbuild),
    ("manual Cloud Run Job deploy", "gcloud run jobs deploy" in deploy),
    ("single task", "--tasks 1" in deploy),
    ("zero retries", "--max-retries 0" in deploy),
    ("Secret Manager mappings", "--set-secrets" in deploy),
]

for label, ok in checks:
    print(f"{'PASS' if ok else 'FAIL'}: {label}")

if not all(ok for _, ok in checks):
    raise SystemExit("RESULT: CLOUD RUN JOB V1 VALIDATION FAILED")
print("RESULT: CLOUD RUN JOB V1 STRUCTURE VALID")
