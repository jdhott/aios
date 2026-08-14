#!/usr/bin/env python3
from pathlib import Path
import ast

root = Path(__file__).resolve().parents[1]
service = (root / "aios/services/review_service.py").read_text()
repo = (root / "aios/review/repository.py").read_text()
inspect = (root / "scripts/app_review_service_inspect.py").read_text()

for text in (service, repo, inspect):
    ast.parse(text)

checks = [
    ("ReviewService exists", "class ReviewService:" in service),
    ("AppReview exists", "class AppReview:" in service),
    ("list_pending_reviews exists", "def list_pending_reviews(" in service),
    ("get_review exists", "def get_review(" in service),
    ("repository general open queue exists", "def get_open_reviews(" in repo),
    ("subject enrichment uses inbox repository", "self.inbox_repository.get_row(" in service),
    ("duplicate actions normalized", all(x in service for x in ['"link_existing"', '"create_anyway"', '"ignore"'])),
    ("clarification options derive from payload", 'payload.get("suggestions")' in service and 'payload.get("proposed_text")' in service),
    ("service has no Notion dependency", "notion" not in service.lower()),
    ("inspection CLI uses service", "ReviewService()" in inspect),
]

for label, ok in checks:
    print(f"{'PASS' if ok else 'FAIL'}: {label}")

if not all(ok for _, ok in checks):
    raise SystemExit("RESULT: APP REVIEW READ SERVICE PHASE 2.1 VALIDATION FAILED")

print("RESULT: APP REVIEW READ SERVICE PHASE 2.1 STRUCTURE VALID")
