#!/usr/bin/env bash
set -euo pipefail
TARGET_DIR="${1:-$PWD}"
cd "$TARGET_DIR"
python3 -m py_compile core/metadata/reconciliation.py
python3 - <<'PY'
from core.metadata.reconciliation import (
    VERSION,
    collect_deprecated_metadata_cleanup_actions,
    collect_governance_anomaly_diagnostics,
)

assert "phase8-1" in VERSION, VERSION

pages = [
    {
        "id": "abc123",
        "properties": {
            "Task Name": {"title": [{"plain_text": "Review recurring charges on Mastercard"}]},
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

actions = collect_deprecated_metadata_cleanup_actions(pages)
assert len(actions) == 1, actions
assert actions[0]["properties"] == {"Strong Candidate": {"checkbox": False}}, actions

anomalies = collect_governance_anomaly_diagnostics(pages)
assert anomalies["counters"]["deprecated_metadata_seen"] == 1, anomalies
print("phase8.1 smoke test passed")
PY
