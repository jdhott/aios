#!/usr/bin/env python3
from pathlib import Path
import ast

root = Path(__file__).resolve().parents[1]
config = (root / "aios/api/config.py").read_text()
app = (root / "aios/api/app.py").read_text()
schema = (root / "aios/api/schemas.py").read_text()
deploy = (root / "scripts/deploy_cloud_run_api.sh").read_text()
cloudbuild = (root / "cloudbuild.api.yaml").read_text()
dockerignore = (root / ".dockerignore").read_text()

for text in (config, app, schema):
    ast.parse(text)

checks = [
    ("security config exists", "class ApiSettings:" in config),
    ("Cloud Run marker validation", 'os.getenv("K_SERVICE")' in config),
    ("Supabase URL validation", 'os.getenv("SUPABASE_URL")' in config),
    ("Supabase server key validation", "SUPABASE_SECRET_KEY" in config),
    ("production forbids local bypass", "cannot be enabled" in config),
    ("startup validates runtime", "validate_runtime_environment()" in app),
    ("health reports auth mode", "auth_mode=settings.auth_mode" in app),
    ("deploy is private", "--no-allow-unauthenticated" in deploy),
    ("deploy never enables public auth", "--allow-unauthenticated" not in deploy),
    ("Secret Manager mapping present", "--set-secrets" in deploy),
    ("Cloud Run env configured", "AIOS_API_ENV=cloudrun" in deploy),
    ("Cloud Build uses API Dockerfile", "Dockerfile.cloudrun-api" in cloudbuild),
    ("dockerignore excludes env files", ".env" in dockerignore and ".env.*" in dockerignore),
]

for label, ok in checks:
    print(f"{'PASS' if ok else 'FAIL'}: {label}")

if not all(ok for _, ok in checks):
    raise SystemExit("RESULT: CLOUD RUN API V1.1 VALIDATION FAILED")

print("RESULT: CLOUD RUN API V1.1 STRUCTURE VALID")
