#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="${1:-$(pwd)}"
cd "$PROJECT_ROOT"

python3 - <<'PY'
from core.metadata import policy
from core.metadata.reconciliation import (
    VERSION,
    scan_pages,
    format_summary,
    _policy_status_lines,
)

assert VERSION == "metadata-reconciliation-phase3-canonical-policy-registry-v0.3.0", VERSION
assert policy.VERSION == "canonical-metadata-policy-v0.1.0", policy.VERSION

sample_pages = [
    {
        "id": "open-today-manual-pin",
        "properties": {
            "Task Name": {"title": [{"plain_text": "Manual Today pin should not be an execution mismatch"}]},
            "Open Loop": {"checkbox": True},
            "Done": {"checkbox": False},
            "Do = Today": {"checkbox": True},
            "Best Next Action": {"checkbox": False},
        },
    },
    {
        "id": "active-ranked",
        "properties": {
            "Task Name": {"title": [{"plain_text": "Active canonical ranked task"}]},
            "Open Loop": {"checkbox": True},
            "Done": {"checkbox": False},
            "Execution Score": {"number": 5},
            "Execution Rank": {"number": 1},
            "Best Next Action": {"checkbox": True},
        },
    },
]
summary = scan_pages(sample_pages)
assert "open_today_without_bna" not in summary.findings, summary.findings
lines = "\n".join(format_summary(summary) + _policy_status_lines())
assert "PHASE 3.0" in lines
assert "Manual-only fields: Do = Today" in lines
assert "Deprecated execution fields ignored" in lines
print("Smoke test passed: canonical metadata policy registry active and manual Today pins ignored.")
PY
