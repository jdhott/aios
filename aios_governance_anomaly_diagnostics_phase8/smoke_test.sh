#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="${1:-$(pwd)}"
cd "$PROJECT_ROOT"

python3 - <<'PY'
from core.metadata.reconciliation import (
    VERSION,
    ReconciliationSummary,
    collect_governance_anomaly_diagnostics,
    format_governance_anomaly_diagnostics,
    format_governance_telemetry_summary,
)

assert VERSION == "metadata-reconciliation-phase8-governance-anomaly-diagnostics-v0.8.0", VERSION

sample_pages = [
    {
        "id": "orphan-today",
        "properties": {
            "Task Name": {"title": [{"plain_text": "Manual today pin without BNA"}]},
            "Open Loop": {"checkbox": True},
            "Done": {"checkbox": False},
            "Do = Today": {"checkbox": True},
            "Best Next Action": {"checkbox": False},
        },
    },
    {
        "id": "quickwin-bna-overlap",
        "properties": {
            "Task Name": {"title": [{"plain_text": "Quick Win BNA overlap"}]},
            "Open Loop": {"checkbox": True},
            "Done": {"checkbox": False},
            "Quick Win": {"checkbox": True},
            "Best Next Action": {"checkbox": True},
            "Execution Rank": {"number": 1},
            "Execution Score": {"number": 8},
        },
    },
    {
        "id": "rank-without-score",
        "properties": {
            "Task Name": {"title": [{"plain_text": "Rank without score"}]},
            "Open Loop": {"checkbox": True},
            "Execution Rank": {"number": 2},
            "Execution Score": {"number": 0},
        },
    },
]

anomalies = collect_governance_anomaly_diagnostics(sample_pages, rank_diag={"duplicates": [1]})
counters = anomalies["counters"]
assert counters["orphaned_today_flags"] == 1, counters
assert counters["quickwin_bna_overlap"] == 1, counters
assert counters["ranked_without_score"] == 1, counters
assert counters["duplicate_execution_ranks"] == 1, counters

lines = "\n".join(format_governance_anomaly_diagnostics(anomalies))
assert "GOVERNANCE ANOMALY DIAGNOSTICS" in lines, lines
assert "Anomaly diagnostics are read-only" in lines, lines

summary_lines = "\n".join(format_governance_telemetry_summary(
    summary=ReconciliationSummary(scanned=3, open_tasks=3),
    presentation_stale_actions=[],
    policy_stale_actions=[],
    rank_actions=[],
    rank_diag={"rows": [], "missing": [], "duplicates": [], "mismatches": []},
    anomalies=anomalies,
))
assert "Anomaly health: total=" in summary_lines, summary_lines
assert "Status: attention_required" in summary_lines, summary_lines
print("Smoke test passed: governance anomaly diagnostics are active and read-only.")
PY
