#!/bin/bash
set -e

echo "=== AIOS PROJECT COGNITION D3.0 RELATION LABEL RESOLUTION ROLLBACK ==="

PROJECT_ROOT="$(pwd)"
BACKUP_DIR="$PROJECT_ROOT/.aios_project_cognition_d3_0_relation_label_resolution_backup"

if [ ! -f "$PROJECT_ROOT/run_aios.py" ]; then
  echo "ERROR: Run this rollback from the AIOS project root, e.g. ~/LocalProjects/aios"
  exit 1
fi

if [ -f "$BACKUP_DIR/aios_project_affinity_report.py" ]; then
  cp "$BACKUP_DIR/aios_project_affinity_report.py" "$PROJECT_ROOT/scripts/aios_project_affinity_report.py"
fi

if [ -f "$BACKUP_DIR/ontology_stabilization_report.py" ]; then
  cp "$BACKUP_DIR/ontology_stabilization_report.py" "$PROJECT_ROOT/tools/ontology_stabilization_report.py"
fi

python3 -m py_compile "$PROJECT_ROOT/tools/ontology_stabilization_report.py"

if [ -f "$PROJECT_ROOT/scripts/aios_project_affinity_report.py" ]; then
  python3 -m py_compile "$PROJECT_ROOT/scripts/aios_project_affinity_report.py"
fi

echo "Rollback complete."
