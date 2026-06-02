#!/bin/bash
set -e

echo "=== AIOS PROJECT COGNITION D3.0 RELATION LABEL RESOLUTION SMOKE TEST ==="

PROJECT_ROOT="$(pwd)"

if [ ! -f "$PROJECT_ROOT/run_aios.py" ]; then
  echo "ERROR: Run this smoke test from the AIOS project root, e.g. ~/LocalProjects/aios"
  exit 1
fi

python3 -m py_compile "$PROJECT_ROOT/tools/repair_project_cognition_snapshot_labels.py"
python3 -m py_compile "$PROJECT_ROOT/tools/ontology_stabilization_report.py"

python3 "$PROJECT_ROOT/tools/repair_project_cognition_snapshot_labels.py" --check
python3 "$PROJECT_ROOT/tools/ontology_stabilization_report.py"

echo "Smoke test completed successfully."
