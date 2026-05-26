#!/usr/bin/env bash
set -euo pipefail
TARGET_DIR="${1:-$PWD}"
cd "$TARGET_DIR"
python3 -m py_compile core/metadata/reconciliation.py
python3 - <<'PY'
from core.metadata.reconciliation import (
    VERSION,
    collect_governance_anomaly_diagnostics,
    collect_deprecated_metadata_cleanup_actions,
    format_governance_observation_baseline,
)

assert "phase8-2" in VERSION, VERSION

clean_pages = [
    {
        "id": "clean123",
        "properties": {
            "Task Name": {"title": [{"plain_text": "Clean governance smoke test task"}]},
            "Open Loop": {"checkbox": True},
            "Done": {"checkbox": False},
            "Strong Candidate": {"checkbox": False},
            "Focus Now": {"checkbox": False},
            "Execution Score": {"number": 8},
            "Execution Rank": {"number": 1},
            "Best Next Action": {"checkbox": True},
            "Quick Win": {"checkbox": False},
            "Do = Today": {"checkbox": True},
        },
    }
]

clean_anomalies = collect_governance_anomaly_diagnostics(clean_pages)
clean_lines = format_governance_observation_baseline(
    anomalies=clean_anomalies,
    presentation_stale_actions=[],
    policy_stale_actions=[],
    deprecated_cleanup_actions=[],
    rank_actions=[],
    cleanup_error_count=0,
)
assert any("status=clean" in line for line in clean_lines), clean_lines
assert any("Observation layer is read-only" in line for line in clean_lines), clean_lines

deprecated_pages = [
    {
        "id": "legacy123",
        "properties": {
            "Task Name": {"title": [{"plain_text": "Legacy metadata smoke test task"}]},
            "Open Loop": {"checkbox": True},
            "Done": {"checkbox": False},
            "Strong Candidate": {"checkbox": True},
            "Focus Now": {"checkbox": False},
            "Execution Score": {"number": None},
            "Execution Rank": {"number": None},
            "Best Next Action": {"checkbox": False},
            "Quick Win": {"checkbox": False},
            "Do = Today": {"checkbox": False},
        },
    }
]
legacy_anomalies = collect_governance_anomaly_diagnostics(deprecated_pages)
legacy_actions = collect_deprecated_metadata_cleanup_actions(deprecated_pages)
legacy_lines = format_governance_observation_baseline(
    anomalies=legacy_anomalies,
    presentation_stale_actions=[],
    policy_stale_actions=[],
    deprecated_cleanup_actions=legacy_actions,
    rank_actions=[],
    cleanup_error_count=0,
)
assert any("status=stabilizing" in line for line in legacy_lines), legacy_lines
assert any("deprecated_cleanup=1" in line for line in legacy_lines), legacy_lines
print("phase8.2 smoke test passed")
PY
