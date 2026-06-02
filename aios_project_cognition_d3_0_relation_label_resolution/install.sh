#!/bin/bash
set -e

echo "=== AIOS PROJECT COGNITION D3.0 RELATION LABEL RESOLUTION INSTALL ==="

PROJECT_ROOT="$(pwd)"
PACKAGE_DIR="$(cd "$(dirname "$0")" && pwd)"

if [ ! -f "$PROJECT_ROOT/run_aios.py" ]; then
  echo "ERROR: Run this installer from the AIOS project root, e.g. ~/LocalProjects/aios"
  exit 1
fi

python3 "$PACKAGE_DIR/install.py"

python3 -m py_compile "$PROJECT_ROOT/tools/repair_project_cognition_snapshot_labels.py"
python3 -m py_compile "$PROJECT_ROOT/tools/ontology_stabilization_report.py"

if [ -f "$PROJECT_ROOT/scripts/aios_project_affinity_report.py" ]; then
  python3 -m py_compile "$PROJECT_ROOT/scripts/aios_project_affinity_report.py"
fi

python3 "$PROJECT_ROOT/tools/repair_project_cognition_snapshot_labels.py"

echo "Install complete."
