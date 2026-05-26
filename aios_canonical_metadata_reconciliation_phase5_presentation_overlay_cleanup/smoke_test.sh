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
    collect_policy_stale_presentation_cleanup_actions,
)

assert VERSION == "metadata-reconciliation-phase5-policy-driven-presentation-overlay-cleanup-v0.5.0", VERSION
assert policy.VERSION == "canonical-metadata-policy-v0.3.0", policy.VERSION

sample_pages = [
    {
        "id": "manual-today-pin",
        "properties": {
            "Task Name": {"title": [{"plain_text": "Manual Today pin should not be touched"}]},
            "Open Loop": {"checkbox": True},
            "Done": {"checkbox": False},
            "Do = Today": {"checkbox": True},
            "Best Next Action": {"checkbox": False},
            "Quick Win": {"checkbox": False},
        },
    },
    {
        "id": "jdi-stale-overlay",
        "properties": {
            "Task Name": {"title": [{"plain_text": "JDI stale overlay should be cleaned"}]},
            "Open Loop": {"checkbox": True},
            "Done": {"checkbox": False},
            "JDI": {"checkbox": True},
            "Quick Win": {"checkbox": True},
            "Do = Today": {"checkbox": True},
        },
    },
    {
        "id": "closed-stale-overlay-and-execution",
        "properties": {
            "Task Name": {"title": [{"plain_text": "Closed stale overlay and execution should be cleaned separately"}]},
            "Open Loop": {"checkbox": False},
            "Done": {"checkbox": True},
            "Quick Win": {"checkbox": True},
            "Execution Score": {"number": 8},
            "Execution Rank": {"number": 2},
            "Best Next Action": {"checkbox": True},
            "Do = Today": {"checkbox": True},
        },
    },
]
summary = scan_pages(sample_pages)
assert "open_today_without_bna" not in summary.findings, summary.findings
presentation_actions = collect_policy_stale_presentation_cleanup_actions(sample_pages)
assert len(presentation_actions) == 2, presentation_actions
for action in presentation_actions:
    assert action["properties"] == {"Quick Win": {"checkbox": False}}, action
    assert "Do = Today" not in action["properties"], action
execution_actions = collect_policy_stale_execution_cleanup_actions(sample_pages)
assert len(execution_actions) == 1, execution_actions
assert "Quick Win" not in execution_actions[0]["properties"], execution_actions
assert "Do = Today" not in execution_actions[0]["properties"], execution_actions
lines = "\n".join(format_summary(summary) + _policy_status_lines())
assert "PHASE 5.0" in lines
assert "Presentation overlays: Quick Win" in lines
assert "Manual-only fields: Do = Today" in lines
print("Smoke test passed: policy-driven presentation overlay cleanup active and manual Today pins preserved.")
PY
