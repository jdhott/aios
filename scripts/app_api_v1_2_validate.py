#!/usr/bin/env python3
from pathlib import Path
import ast

root = Path(__file__).resolve().parents[1]
app = (root / "aios/api/app.py").read_text()
schemas = (root / "aios/api/schemas.py").read_text()
service = (root / "aios/services/review_service.py").read_text()

for text in (app, schemas, service):
    ast.parse(text)

checks = [
    ("v1.2 marker", 'AIOS_API_REVIEW_RESOLUTION_VERSION = "cloud-run-api-v1.2"' in app),
    ("duplicate endpoint", '"/reviews/{review_id}/possible-duplicate"' in app),
    ("clarification awaiting endpoint", '"/reviews/{review_id}/clarification/awaiting-answer"' in app),
    ("clarification confirmation endpoint", '"/reviews/{review_id}/clarification/pending-confirmation"' in app),
    ("clarification resolve endpoint", '"/reviews/{review_id}/clarification/resolve"' in app),
    ("duplicate uses ReviewService", "_review_service().resolve_possible_duplicate(" in app),
    ("terminal duplicate marks inbox processed", "_mark_review_inbox_processed(response)" in app),
    ("request schemas", "class PossibleDuplicateResolutionRequest" in schemas and "class ClarificationResolutionRequest" in schemas),
    ("service boundary present", "def resolve_possible_duplicate(" in service and "def resolve_clarification(" in service),
    ("API remains Notion-independent", "from aios.notion" not in app and "import notion" not in app),
]

for label, ok in checks:
    print(f"{'PASS' if ok else 'FAIL'}: {label}")

if not all(ok for _, ok in checks):
    raise SystemExit("RESULT: CLOUD RUN API V1.2 VALIDATION FAILED")
print("RESULT: CLOUD RUN API V1.2 STRUCTURE VALID")
