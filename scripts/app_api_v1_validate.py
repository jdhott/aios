#!/usr/bin/env python3
from pathlib import Path
import ast

root = Path(__file__).resolve().parents[1]

app = (root / "aios/api/app.py").read_text()
schemas = (root / "aios/api/schemas.py").read_text()
dockerfile = (root / "Dockerfile.cloudrun-api").read_text()
requirements = (root / "requirements-api.txt").read_text()
dockerignore = (root / ".dockerignore.aios-api").read_text()

ast.parse(app)
ast.parse(schemas)

checks = [
    ("FastAPI app exists", "app = FastAPI(" in app),
    ("health endpoint exists", '@app.get(' in app and '"/health"' in app),
    ("capture endpoint exists", '@app.post(' in app and '"/inbox"' in app),
    ("review list endpoint exists", '"/reviews"' in app),
    ("single review endpoint exists", '"/reviews/{review_id}"' in app),
    ("capture uses canonical parser", "parser=parse_capture_metadata" in app),
    ("capture uses source-neutral inbox repository", "InboxRepository" in app),
    ("reviews use ReviewService", "ReviewService" in app),
    ("API has no Notion dependency", "from aios.notion" not in app and "import notion" not in app),
    ("FastAPI dependency declared", "fastapi" in requirements.lower()),
    ("Uvicorn dependency declared", "uvicorn" in requirements.lower()),
    ("Cloud Run container listens on PORT", "${PORT}" in dockerfile),
    ("Docker build excludes .env", ".env" in dockerignore),
]

for label, ok in checks:
    print(f"{'PASS' if ok else 'FAIL'}: {label}")

if not all(ok for _, ok in checks):
    raise SystemExit("RESULT: CLOUD RUN API V1 VALIDATION FAILED")

print("RESULT: CLOUD RUN API V1 STRUCTURE VALID")
