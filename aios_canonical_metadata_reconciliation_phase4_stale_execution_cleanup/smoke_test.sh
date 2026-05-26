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
    collect_policy_stale_execution_cleanup_actions,
)

assert VERSION == "metadata-reconciliation-phase4-policy-driven-stale-execution-cleanup-v0.4.0", VERSION
assert policy.VERSION == "canonical-metadata-policy-v0.2.0", policy.VERSION

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
        "id": "jdi-stale-execution",
        "properties": {
            "Task Name": {"title": [{"plain_text": "JDI stale execution should be cleaned"}]},
            "Open Loop": {"checkbox": True},
            "Done": {"checkbox": False},
            "JDI": {"checkbox": True},
            "Execution Score": {"number": 7},
            "Execution Rank": {"number": 3},
            "Best Next Action": {"checkbox": True},
            "Do = Today": {"checkbox": True},
        },
    },
]
summary = scan_pages(sample_pages)
assert "open_today_without_bna" not in summary.findings, summary.findings
actions = collect_policy_stale_execution_cleanup_actions(sample_pages)
assert len(actions) == 1, actions
props = actions[0]["properties"]
assert props["Execution Score"] == {"number": None}, props
assert props["Execution Rank"] == {"number": None}, props
assert props["Best Next Action"] == {"checkbox": False}, props
assert "Do = Today" not in props, props
lines = "\n".join(format_summary(summary) + _policy_status_lines())
assert "PHASE 4.0" in lines
assert "Manual-only fields: Do = Today" in lines
assert "Deprecated execution fields ignored" in lines
print("Smoke test passed: policy-driven stale execution cleanup active and manual Today pins preserved.")
PY
