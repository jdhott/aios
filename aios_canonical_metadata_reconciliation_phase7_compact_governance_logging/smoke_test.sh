#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="${1:-$(pwd)}"
cd "$PROJECT_ROOT"

python3 - <<'PY'
import io
import os
import contextlib
from core.metadata import policy
from core.metadata.reconciliation import (
    VERSION,
    scan_pages,
    format_governance_telemetry_summary,
    format_execution_rank_diagnostics,
)
import execution_engine_v2

assert VERSION == "metadata-reconciliation-phase7-compact-governance-logging-v0.7.0", VERSION
assert policy.VERSION == "canonical-metadata-policy-v0.4.1", policy.VERSION

rank_diag = {
    "rows": [
        {"current_rank": 1, "score": 10, "short_id": "abc", "title": "One", "best_next": True, "parentish": False},
        {"current_rank": 2, "score": 8, "short_id": "def", "title": "Two", "best_next": False, "parentish": True},
    ],
    "by_rank": [
        {"current_rank": 1, "score": 10, "short_id": "abc", "title": "One", "best_next": True, "parentish": False},
        {"current_rank": 2, "score": 8, "short_id": "def", "title": "Two", "best_next": False, "parentish": True},
    ],
    "deterministic": [
        {"current_rank": 1, "score": 10, "short_id": "abc", "title": "One", "best_next": True, "parentish": False},
        {"current_rank": 2, "score": 8, "short_id": "def", "title": "Two", "best_next": False, "parentish": True},
    ],
    "missing": [],
    "duplicates": [],
    "skipped": {"closed_or_done": 1, "jdi": 2},
    "mismatches": [],
}

os.environ.pop("AIOS_VERBOSE_RANK_DIAGNOSTICS", None)
compact = "\n".join(format_execution_rank_diagnostics(rank_diag))
assert "Detailed row previews suppressed" in compact, compact
assert "Rank-order row:" not in compact, compact
assert "Deterministic row:" not in compact, compact

os.environ["AIOS_VERBOSE_RANK_DIAGNOSTICS"] = "true"
verbose = "\n".join(format_execution_rank_diagnostics(rank_diag))
assert "Rank-order row:" in verbose, verbose
assert "Deterministic row:" in verbose, verbose
os.environ.pop("AIOS_VERBOSE_RANK_DIAGNOSTICS", None)

sample_pages = [
    {"id": "open", "properties": {"Task Name": {"title": [{"plain_text": "Open task"}]}, "Open Loop": {"checkbox": True}, "Done": {"checkbox": False}}}
]
summary = scan_pages(sample_pages)
telemetry = "\n".join(format_governance_telemetry_summary(
    summary=summary,
    presentation_stale_actions=[],
    policy_stale_actions=[],
    rank_actions=[],
    rank_diag=rank_diag,
))
assert "METADATA GOVERNANCE TELEMETRY SUMMARY" in telemetry, telemetry
assert "Status: clean" in telemetry, telemetry

assert execution_engine_v2._verbose_execution_diagnostics_enabled() is False
os.environ["AIOS_VERBOSE_EXECUTION_DIAGNOSTICS"] = "true"
assert execution_engine_v2._verbose_execution_diagnostics_enabled() is True
os.environ.pop("AIOS_VERBOSE_EXECUTION_DIAGNOSTICS", None)

print("Smoke test passed: compact governance logging active; verbose diagnostics remain opt-in.")
PY
