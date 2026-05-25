#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="${1:-$PWD}"
PACKAGE_DIR="$(cd "$(dirname "$0")" && pwd)"
STAMP="$(date +%Y%m%d_%H%M%S)"
BACKUP_DIR="$PROJECT_ROOT/backups/metadata_reconciliation_phase1_5_$STAMP"
RUN_FILE="$PROJECT_ROOT/run_aios.py"
BOOTSTRAP_FILE="$PACKAGE_DIR/patches/metadata_reconciliation_bootstrap.py"
MARKER="AIOS METADATA RECONCILIATION PHASE 1 BOOTSTRAP"

cd "$PROJECT_ROOT"
mkdir -p "$BACKUP_DIR"

echo "=== AIOS Metadata Reconciliation Phase 1.5 Installer ==="
echo "Project root: $PROJECT_ROOT"
echo "Backup dir:   $BACKUP_DIR"

if [[ ! -f "$RUN_FILE" ]]; then
  echo "ERROR: run_aios.py not found in $PROJECT_ROOT"
  echo "Run this installer from ~/LocalProjects/aios or pass the project root as the first argument."
  exit 1
fi

cp "$RUN_FILE" "$BACKUP_DIR/run_aios.py.bak"
if [[ -d "$PROJECT_ROOT/core" ]]; then
  cp -R "$PROJECT_ROOT/core" "$BACKUP_DIR/core.bak"
fi

mkdir -p "$PROJECT_ROOT/core/metadata"
if [[ ! -f "$PROJECT_ROOT/core/__init__.py" ]]; then
  cp "$PACKAGE_DIR/core/__init__.py" "$PROJECT_ROOT/core/__init__.py"
fi
if [[ ! -f "$PROJECT_ROOT/core/metadata/__init__.py" ]]; then
  cp "$PACKAGE_DIR/core/metadata/__init__.py" "$PROJECT_ROOT/core/metadata/__init__.py"
fi
cp "$PACKAGE_DIR/core/metadata/reconciliation.py" "$PROJECT_ROOT/core/metadata/reconciliation.py"

mkdir -p "$PROJECT_ROOT/tools"
cp "$PACKAGE_DIR/tools/smoke_test_metadata_reconciliation.py" "$PROJECT_ROOT/tools/smoke_test_metadata_reconciliation.py"
cp "$PACKAGE_DIR/rollback.sh" "$PROJECT_ROOT/tools/rollback_metadata_reconciliation_phase1.sh"
chmod +x "$PROJECT_ROOT/tools/smoke_test_metadata_reconciliation.py"
chmod +x "$PROJECT_ROOT/tools/rollback_metadata_reconciliation_phase1.sh"

if grep -q "$MARKER" "$RUN_FILE"; then
  echo "Bootstrap already present in run_aios.py; leaving existing hook in place."
else
  cat "$BOOTSTRAP_FILE" >> "$RUN_FILE"
  echo "Installed metadata reconciliation bootstrap into run_aios.py"
fi

cat > "$BACKUP_DIR/ROLLBACK_INSTRUCTIONS.txt" <<EOF
Rollback created by metadata reconciliation phase 1.5 installer.

To rollback:
  cd "$PROJECT_ROOT"
  cp "$BACKUP_DIR/run_aios.py.bak" "$PROJECT_ROOT/run_aios.py"
  if [ -d "$BACKUP_DIR/core.bak" ]; then rm -rf "$PROJECT_ROOT/core" && cp -R "$BACKUP_DIR/core.bak" "$PROJECT_ROOT/core"; fi
EOF

echo "$BACKUP_DIR" > "$PROJECT_ROOT/.metadata_reconciliation_phase1_5_last_backup"

echo "Running smoke test..."
"${PYTHON:-python3}" "$PROJECT_ROOT/tools/smoke_test_metadata_reconciliation.py"

echo "Install complete. Next test command:"
echo "cd $PROJECT_ROOT"
echo "bash run.sh > test_run.log 2>&1"
echo "grep -E 'METADATA RECONCILIATION|Metadata Reconciliation|Closed/done|Done tasks|Deferred future|Would clear Quick Win|Applying Quick Win|Clearing Quick Win|Quick Win cleared|Mutation error' test_run.log"
