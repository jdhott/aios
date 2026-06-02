#!/usr/bin/env bash
set -euo pipefail

ROOT="${1:-$PWD}"
cd "$ROOT"

python3 -m py_compile execution_engine_v2.py run_aios.py core/evaluator.py aios/clarification.py

if grep -RIn "Priority" execution_engine_v2.py core/evaluator.py run_aios.py aios/clarification.py >/tmp/aios_priority_hits.txt; then
  echo "ERROR: Legacy Priority reference remains in canonical execution files:" >&2
  cat /tmp/aios_priority_hits.txt >&2
  exit 1
fi

if grep -RIn '"Due"\|\x27Due\x27' execution_engine_v2.py core/evaluator.py run_aios.py aios/clarification.py >/tmp/aios_due_hits.txt; then
  echo "ERROR: Legacy Due reference remains in canonical execution files:" >&2
  cat /tmp/aios_due_hits.txt >&2
  exit 1
fi

python3 - <<'PY'
from execution_engine_v2 import compute_execution_score

def notion_select(name):
    return {"select": {"name": name}}

def notion_date(value):
    return {"date": {"start": value}}

canonical = {
    "properties": {
        "Importance": notion_select("High Importance"),
        "Urgency": notion_select("High Urgency"),
    }
}
score = compute_execution_score(canonical)
assert score["score"] == 50, score
assert "high_importance" in score["reasons"], score
assert "high_urgency" in score["reasons"], score

legacy_priority_only = {
    "properties": {
        "Priority": notion_select("High Priority"),
    }
}
score = compute_execution_score(legacy_priority_only)
assert score["score"] == 0, score

canonical_due = {
    "properties": {
        "Due Date": notion_date("2000-01-01"),
    }
}
score = compute_execution_score(canonical_due)
assert score["score"] == 30, score
assert "due_today_or_overdue" in score["reasons"], score

legacy_due = {
    "properties": {
        "Due": notion_date("2000-01-01"),
    }
}
score = compute_execution_score(legacy_due)
assert score["score"] == 0, score

print("Canonical execution metadata smoke tests passed.")
PY

echo "Smoke test complete."
