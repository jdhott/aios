#!/usr/bin/env python3
from pathlib import Path
import ast

root = Path(__file__).resolve().parents[1]

app = (root / "aios/web_capture/app.py").read_text()
docker = (root / "Dockerfile.cloudrun-web").read_text()
requirements = (root / "requirements-web.txt").read_text()
deploy = (root / "scripts/deploy_cloud_run_web.sh").read_text()
configure = (root / "scripts/configure_cloud_run_web.sh").read_text()

ast.parse(app)

checks = [
    ("web capture app exists", "WEB_CAPTURE_VERSION" in app),
    ("health endpoint exists", '@app.get("/health")' in app),
    ("brain dump page exists", '@app.get("/", response_class=HTMLResponse)' in app),
    ("submit endpoint exists", '@app.post("/submit")' in app),
    ("HTTP Basic authentication exists", "HTTPBasic" in app),
    ("password uses constant-time comparison", "hmac.compare_digest" in app),
    ("private AIOS API called server-side", 'f"{api_url}/inbox"' in app),
    ("Google ID token used for API", "fetch_id_token" in app),
    ("POST/redirect/GET protects refresh", "status_code=303" in app),
    ("browser button disables on submit", "submitButton.disabled=true" in app),
    ("web requirements include google-auth", "google-auth" in requirements),
    ("web requirements include form parser", "python-multipart" in requirements),
    ("Cloud Run Dockerfile listens on PORT", "${PORT:-8080}" in docker),
    ("deploy uses dedicated runtime service account", "aios-web-runtime" in deploy),
    ("web service is publicly reachable", "--allow-unauthenticated" in deploy),
    ("password comes from Secret Manager", "AIOS_WEB_PASSWORD=aios-web-password:latest" in deploy),
    ("runtime gets API invoker permission", "roles/run.invoker" in configure),
    ("runtime gets password secret access", "roles/secretmanager.secretAccessor" in configure),
]

for label, ok in checks:
    print(f"{'PASS' if ok else 'FAIL'}: {label}")

if not all(ok for _, ok in checks):
    raise SystemExit("RESULT: AIOS WEB CAPTURE V1 VALIDATION FAILED")

print("RESULT: AIOS WEB CAPTURE V1 STRUCTURE VALID")
